Predictor
=========

.. seealso::

    See this :ref:`user guide on performing model inference <air-predictors>` in
    AIR for usage examples.

.. currentmodule:: ray.train

Predictor Interface
-------------------

Constructor Options
~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/
    :template: autosummary/class_with_autosummary.rst

    predictor.Predictor

.. autosummary::
    :toctree: doc/

    predictor.Predictor.from_checkpoint
    predictor.Predictor.from_pandas_udf

Predictor Properties
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/

    predictor.Predictor.get_preprocessor
    predictor.Predictor.set_preprocessor


Prediction API
~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/

    predictor.Predictor.predict


Supported Data Formats
~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/

    predictor.Predictor.preferred_batch_format
    ~predictor.DataBatchType


Batch Predictor
---------------

Constructor
~~~~~~~~~~~

.. autosummary::
    :toctree: doc/
    :template: autosummary/class_with_autosummary.rst

    batch_predictor.BatchPredictor


Batch Prediction API
~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/

    batch_predictor.BatchPredictor.predict
    batch_predictor.BatchPredictor.predict_pipelined


Built-in Predictors for Library Integrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autosummary::
    :toctree: doc/

    ~xgboost.XGBoostPredictor
    ~lightgbm.LightGBMPredictor
    ~tensorflow.TensorflowPredictor
    ~torch.TorchPredictor
    ~huggingface.HuggingFacePredictor
    ~sklearn.SklearnPredictor
    ~rl.RLPredictor
