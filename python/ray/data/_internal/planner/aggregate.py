from typing import List, Optional, Tuple

from ray.data._internal.execution.interfaces import (
    AllToAllTransformFn,
    RefBundle,
    TaskContext,
)
from ray.data._internal.planner.exchange.aggregate_task_spec import (
    SortAggregateTaskSpec,
)
from ray.data._internal.planner.exchange.push_based_shuffle_task_scheduler import (
    PushBasedShuffleTaskScheduler,
)
from ray.data._internal.planner.exchange.pull_based_shuffle_task_scheduler import (
    PullBasedShuffleTaskScheduler,
)
from ray.data._internal.planner.exchange.sort_task_spec import SortTaskSpec
from ray.data._internal.stats import StatsDict
from ray.data.aggregate import AggregateFn
from ray.data.block import KeyFn
from ray.data.context import DatasetContext


def generate_aggregate_fn(
    key: Optional[KeyFn],
    aggs: List[AggregateFn],
) -> AllToAllTransformFn:
    """Generate function to aggregate blocks by the specified key column or key
    function.
    """
    # TODO: validate blocks with AggregateFn._validate.
    if len(aggs) == 0:
        raise ValueError("Aggregate requires at least one aggregation")

    def fn(
        refs: List[RefBundle],
        ctx: TaskContext,
    ) -> Tuple[List[RefBundle], StatsDict]:
        blocks = []
        for ref_bundle in refs:
            for block, _ in ref_bundle.blocks:
                blocks.append(block)
        if len(blocks) == 0:
            return (blocks, {})

        num_mappers = len(blocks)

        if key is None:
            num_outputs = 1
            boundaries = []
        else:
            # Use same number of output partitions.
            num_outputs = num_mappers
            # Sample boundaries for aggregate key.
            boundaries = SortTaskSpec.sample_boundaries(
                blocks,
                [(key, "ascending")] if isinstance(key, str) else key,
                num_outputs,
            )

        agg_spec = SortAggregateTaskSpec(
            boundaries=boundaries,
            key=key,
            aggs=aggs,
        )
        if DatasetContext.get_current().use_push_based_shuffle:
            scheduler = PushBasedShuffleTaskScheduler(agg_spec)
        else:
            scheduler = PullBasedShuffleTaskScheduler(agg_spec)

        return scheduler.execute(refs, num_outputs)

    return fn
