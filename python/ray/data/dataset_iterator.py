import abc
import numpy as np
import sys
from typing import TYPE_CHECKING, Dict, List, Optional, Union, Iterator

from ray.air.util.data_batch_conversion import BlockFormat
from ray.data.block import DataBatch
from ray.util.annotations import PublicAPI

if TYPE_CHECKING:
    import tensorflow as tf
    import torch
    from ray.data._internal.torch_iterable_dataset import TorchTensorBatchType
    from ray.data.dataset import Dataset
    from ray.data.dataset_pipeline import DatasetPipeline
    from ray.train._internal.dataset_iterator import TrainDatasetIterator


if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


@PublicAPI(stability="beta")
class DatasetIterator(abc.ABC):
    """An iterator for reading items from a :class:`~Dataset` or
    :class:`~DatasetPipeline`.

    For Datasets, each iteration call represents a complete read of all items in the
    Dataset. For DatasetPipelines, each iteration call represents one pass (epoch)
    over the base Dataset. Note that for DatasetPipelines, each pass iterates over
    the original Dataset, instead of a window (if ``.window()`` was used).

    If using Ray AIR, each trainer actor should get its own iterator by calling
    :meth:`session.get_dataset_shard("train")
    <ray.air.session.get_dataset_shard>`.

    Examples:
        >>> import ray
        >>> ds = ray.data.range(5)
        >>> ds
        Dataset(num_blocks=5, num_rows=5, schema=<class 'int'>)
        >>> ds.iterator()
        DatasetIterator(Dataset(num_blocks=5, num_rows=5, schema=<class 'int'>))
        >>> ds = ds.repeat(); ds
        DatasetPipeline(num_windows=inf, num_stages=2)
        >>> ds.iterator()
        DatasetIterator(DatasetPipeline(num_windows=inf, num_stages=2))

    .. tip::
        For debugging purposes, use
        :meth:`~ray.air.util.check_ingest.make_local_dataset_iterator` to create a
        local `DatasetIterator` from a :class:`~ray.data.Dataset`, a
        :class:`~ray.data.Preprocessor`, and a :class:`~ray.air.DatasetConfig`.
    """

    @abc.abstractmethod
    def iter_batches(
        self,
        *,
        prefetch_blocks: int = 0,
        batch_size: int = 256,
        batch_format: Literal["default", "numpy", "pandas"] = "default",
        drop_last: bool = False,
        local_shuffle_buffer_size: Optional[int] = None,
        local_shuffle_seed: Optional[int] = None,
    ) -> Iterator[DataBatch]:
        """Return a local batched iterator over the dataset.

        Examples:
            >>> import ray
            >>> for batch in ray.data.range(
            ...     1000000
            ... ).iterator().iter_batches(): # doctest: +SKIP
            ...     print(batch) # doctest: +SKIP

        Time complexity: O(1)

        Args:
            prefetch_blocks: The number of blocks to prefetch ahead of the
                current block during the scan.
            batch_size: The number of rows in each batch, or None to use entire blocks
                as batches (blocks may contain different number of rows).
                The final batch may include fewer than ``batch_size`` rows if
                ``drop_last`` is ``False``. Defaults to 256.
            batch_format: The format in which to return each batch.
                Specify "default" to use the default block format (promoting
                tables to Pandas and tensors to NumPy), "pandas" to select
                ``pandas.DataFrame``, "pyarrow" to select ``pyarrow.Table``, or "numpy"
                to select ``numpy.ndarray`` for tensor datasets and
                ``Dict[str, numpy.ndarray]`` for tabular datasets. Default is "default".
            drop_last: Whether to drop the last batch if it's incomplete.
            local_shuffle_buffer_size: If non-None, the data will be randomly shuffled
                using a local in-memory shuffle buffer, and this value will serve as the
                minimum number of rows that must be in the local in-memory shuffle
                buffer in order to yield a batch. When there are no more rows to add to
                the buffer, the remaining rows in the buffer will be drained.
            local_shuffle_seed: The seed to use for the local random shuffle.

        Returns:
            An iterator over record batches.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def iter_torch_batches(
        self,
        *,
        prefetch_blocks: int = 0,
        batch_size: Optional[int] = 256,
        dtypes: Optional[Union["torch.dtype", Dict[str, "torch.dtype"]]] = None,
        device: Optional[str] = None,
        drop_last: bool = False,
        local_shuffle_buffer_size: Optional[int] = None,
        local_shuffle_seed: Optional[int] = None,
    ) -> Iterator["TorchTensorBatchType"]:
        """Return a local batched iterator of Torch Tensors over the dataset.

        This iterator will yield single-tensor batches if the underlying dataset
        consists of a single column; otherwise, it will yield a dictionary of
        column-tensors. If looking for more flexibility in the tensor conversion (e.g.
        casting dtypes) or the batch format, try using `.iter_batches` directly.

        Examples:
            >>> import ray
            >>> for batch in ray.data.range( # doctest: +SKIP
            ...     12,
            ... ).iterator().iter_torch_batches(batch_size=4):
            ...     print(batch.shape) # doctest: +SKIP
            torch.Size([4, 1])
            torch.Size([4, 1])
            torch.Size([4, 1])

        Time complexity: O(1)

        Args:
            prefetch_blocks: The number of blocks to prefetch ahead of the
                current block during the scan.
            batch_size: The number of rows in each batch, or None to use entire blocks
                as batches (blocks may contain different number of rows).
                The final batch may include fewer than ``batch_size`` rows if
                ``drop_last`` is ``False``. Defaults to 256.
            dtypes: The Torch dtype(s) for the created tensor(s); if None, the dtype
                will be inferred from the tensor data.
            device: The device on which the tensor should be placed; if None, the Torch
                tensor will be constructed on the CPU.
            drop_last: Whether to drop the last batch if it's incomplete.
            local_shuffle_buffer_size: If non-None, the data will be randomly shuffled
                using a local in-memory shuffle buffer, and this value will serve as the
                minimum number of rows that must be in the local in-memory shuffle
                buffer in order to yield a batch. When there are no more rows to add to
                the buffer, the remaining rows in the buffer will be drained. This
                buffer size must be greater than or equal to ``batch_size``, and
                therefore ``batch_size`` must also be specified when using local
                shuffling.
            local_shuffle_seed: The seed to use for the local random shuffle.

        Returns:
            An iterator over Torch Tensor batches.
        """
        raise NotImplementedError

    def to_tf(
        self,
        feature_columns: Union[str, List[str]],
        label_columns: Union[str, List[str]],
        *,
        prefetch_blocks: int = 0,
        batch_size: int = 1,
        drop_last: bool = False,
        local_shuffle_buffer_size: Optional[int] = None,
        local_shuffle_seed: Optional[int] = None,
    ) -> "tf.data.Dataset":
        """Return a TF Dataset over this dataset.

        .. warning::
            If your dataset contains ragged tensors, this method errors. To prevent
            errors, resize tensors or
            :ref:`disable tensor extension casting <disable_tensor_extension_casting>`.

        Examples:
            >>> import ray
            >>> ds = ray.data.read_csv(
            ...     "s3://anonymous@air-example-data/iris.csv"
            ... )
            >>> it = ds.iterator(); it
            DatasetIterator(Dataset(num_blocks=1, num_rows=150, schema={sepal length (cm): double, sepal width (cm): double, petal length (cm): double, petal width (cm): double, target: int64}))

            If your model accepts a single tensor as input, specify a single feature column.

            >>> it.to_tf(feature_columns="sepal length (cm)", label_columns="target")  # doctest: +SKIP
            <_OptionsDataset element_spec=(TensorSpec(shape=(None,), dtype=tf.float64, name='sepal length (cm)'), TensorSpec(shape=(None,), dtype=tf.int64, name='target'))>

            If your model accepts a dictionary as input, specify a list of feature columns.

            >>> it.to_tf(["sepal length (cm)", "sepal width (cm)"], "target")  # doctest: +SKIP
            <_OptionsDataset element_spec=({'sepal length (cm)': TensorSpec(shape=(None,), dtype=tf.float64, name='sepal length (cm)'), 'sepal width (cm)': TensorSpec(shape=(None,), dtype=tf.float64, name='sepal width (cm)')}, TensorSpec(shape=(None,), dtype=tf.int64, name='target'))>

            If your dataset contains multiple features but your model accepts a single
            tensor as input, combine features with
            :class:`~ray.data.preprocessors.Concatenator`.

            >>> from ray.data.preprocessors import Concatenator
            >>> preprocessor = Concatenator(output_column_name="features", exclude="target")
            >>> it = preprocessor.transform(ds).iterator()
            >>> it
            DatasetIterator(Dataset(num_blocks=1, num_rows=150, schema={target: int64, features: TensorDtype(shape=(4,), dtype=float64)}))
            >>> it.to_tf("features", "target")  # doctest: +SKIP
            <_OptionsDataset element_spec=(TensorSpec(shape=(None, 4), dtype=tf.float64, name='features'), TensorSpec(shape=(None,), dtype=tf.int64, name='target'))>

        Args:
            feature_columns: Columns that correspond to model inputs. If this is a
                string, the input data is a tensor. If this is a list, the input data
                is a ``dict`` that maps column names to their tensor representation.
            label_column: Columns that correspond to model targets. If this is a
                string, the target data is a tensor. If this is a list, the target data
                is a ``dict`` that maps column names to their tensor representation.
            prefetch_blocks: The number of blocks to prefetch ahead of the
                current block during the scan.
            batch_size: Record batch size. Defaults to 1.
            drop_last: Set to True to drop the last incomplete batch,
                if the dataset size is not divisible by the batch size. If
                False and the size of dataset is not divisible by the batch
                size, then the last batch will be smaller. Defaults to False.
            local_shuffle_buffer_size: If non-None, the data will be randomly shuffled
                using a local in-memory shuffle buffer, and this value will serve as the
                minimum number of rows that must be in the local in-memory shuffle
                buffer in order to yield a batch. When there are no more rows to add to
                the buffer, the remaining rows in the buffer will be drained. This
                buffer size must be greater than or equal to ``batch_size``, and
                therefore ``batch_size`` must also be specified when using local
                shuffling.
            local_shuffle_seed: The seed to use for the local random shuffle.

        Returns:
            A ``tf.data.Dataset`` that yields inputs and targets.
        """  # noqa: E501

        from ray.air._internal.tensorflow_utils import (
            get_type_spec,
            convert_ndarray_to_tf_tensor,
        )

        try:
            import tensorflow as tf
        except ImportError:
            raise ValueError("tensorflow must be installed!")

        base_dataset = self._base_dataset_or_pipeline

        if base_dataset.dataset_format() == BlockFormat.SIMPLE:
            raise NotImplementedError(
                "`to_tf` doesn't support simple datasets. Call `map_batches` and "
                "convert your data to a tabular format. Alternatively, call the more-"
                "flexible `iter_batches` in place of `to_tf`."
            )

        if base_dataset._is_tensor_dataset():
            raise NotImplementedError(
                "`to_tf` doesn't support single-column tensor datasets. Call the "
                "more-flexible `iter_batches` instead."
            )

        schema = base_dataset.schema()
        valid_columns = schema.names

        def validate_column(column: str) -> None:
            if column not in valid_columns:
                raise ValueError(
                    f"You specified '{column}' in `feature_columns` or "
                    f"`label_columns`, but there's no column named '{column}' in the "
                    f"dataset. Valid column names are: {valid_columns}."
                )

        def validate_columns(columns: Union[str, List]) -> None:
            if isinstance(columns, list):
                for column in columns:
                    validate_column(column)
            else:
                validate_column(columns)

        validate_columns(feature_columns)
        validate_columns(label_columns)

        def convert_batch_to_tensors(
            batch: Dict[str, np.ndarray],
            *,
            columns: Union[str, List[str]],
            type_spec: Union[tf.TypeSpec, Dict[str, tf.TypeSpec]],
        ) -> Union[tf.Tensor, Dict[str, tf.Tensor]]:
            if isinstance(columns, str):
                return convert_ndarray_to_tf_tensor(batch[columns], type_spec=type_spec)
            return {
                column: convert_ndarray_to_tf_tensor(
                    batch[column], type_spec=type_spec[column]
                )
                for column in columns
            }

        def generator():
            for batch in self.iter_batches(
                prefetch_blocks=prefetch_blocks,
                batch_size=batch_size,
                drop_last=drop_last,
                local_shuffle_buffer_size=local_shuffle_buffer_size,
                local_shuffle_seed=local_shuffle_seed,
                batch_format="numpy",
            ):
                assert isinstance(batch, dict)
                features = convert_batch_to_tensors(
                    batch, columns=feature_columns, type_spec=feature_type_spec
                )
                labels = convert_batch_to_tensors(
                    batch, columns=label_columns, type_spec=label_type_spec
                )
                yield features, labels

        feature_type_spec = get_type_spec(schema, columns=feature_columns)
        label_type_spec = get_type_spec(schema, columns=label_columns)
        output_signature = (feature_type_spec, label_type_spec)

        dataset = tf.data.Dataset.from_generator(
            generator, output_signature=output_signature
        )

        options = tf.data.Options()
        options.experimental_distribute.auto_shard_policy = (
            tf.data.experimental.AutoShardPolicy.OFF
        )
        return dataset.with_options(options)

    @abc.abstractmethod
    def stats(self) -> str:
        """Returns a string containing execution timing information."""
        raise NotImplementedError

    @property
    def _base_dataset_or_pipeline(self) -> Union["Dataset", "DatasetPipeline"]:
        """The :class:`~ray.data.dataset.Dataset` or
        :class:`~ray.data.dataset.DatasetPipeline` that this object iterates over."""
        raise NotImplementedError

    def iter_epochs(self, max_epoch: int = -1) -> None:
        raise DeprecationWarning(
            "If you are using AIR, note that session.get_dataset_shard() "
            "returns a ray.data.DatasetIterator instead of a "
            "DatasetPipeline as of Ray 2.3. "
            "To iterate over one epoch of data, use iter_batches(), "
            "iter_torch_batches(), or to_tf()."
        )

    def _to_train_iterator(self) -> "TrainDatasetIterator":
        """
        Convert this DatasetIterator to one that is specific
        to Ray Train Trainers.

        The Train-specific iterator has training specific logic,
        for example, automatically moving batches to GPU when GPU training
        is enabled.
        """
        raise NotImplementedError
