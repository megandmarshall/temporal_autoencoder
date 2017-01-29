
import tensorflow as tf

class CRNNCell(object):
  """CRNN cell.
  """

  def __call__(self, inputs, state, scope=None):
    """Run this RNN cell on inputs, starting from the inputted state.
    """
    raise NotImplementedError("Abstract method")

  @property
  def state_size(self):
    """sizes of states used by cell.
    """
    raise NotImplementedError("Abstract method")

  @property
  def output_size(self):
    """Integer or TensorShape: size of outputs produced by cell."""
    raise NotImplementedError("Abstract method")

  def set_zero_state(self, batch_size, dtype):
    """Return zero-filled state tensor(s).
    Args:
      batch_size: int, float, or unit Tensor representing batch size.
      dtype: data type for the state.
    Returns:
      tensor with shape '[batch_size x shape[0] x shape[1] x features]
      filled with zeros
    """
    
    shape = self.shape 
    features = self.features
    zeros = tf.zeros([batch_size, shape[0], shape[1], features * 2]) 
    return zeros

class clstm(CRNNCell):
  """CNN LSTM network's single cell.
  """

# https://github.com/tensorflow/tensorflow/blob/master/tensorflow/contrib/rnn/python/ops/core_rnn_cell_impl.py

  def __init__(self, shape, filter_size, features, forget_bias=1.0, input_size=None,
               state_is_tuple=False, activation=tf.nn.tanh):
    """Initialize the basic CLSTM cell.
    Args:
      shape: int tuple of the height and width of the cell
      filter_size: int tuple of the height and width of the filter
      features: int of the depth of the cell 
      forget_bias: float, the bias added to forget gates (see above).
      input_size: Deprecated.
      state_is_tuple: If True, accepted and returned states are 2-tuples of
        the `c_state` and `m_state`.  If False, they are concatenated
        along the column axis.  Soon deprecated.
      activation: Activation function of inner states.
    """
    if input_size is not None:
      logging.warn("%s: Input_size parameter is deprecated.", self)
    self.shape = shape 
    self.filter_size = filter_size
    self.features = features 
    self._forget_bias = forget_bias
    self._state_is_tuple = state_is_tuple
    self._activation = activation

  @property
  def state_size(self):
    return (LSTMStateTuple(self._num_units, self._num_units)
            if self._state_is_tuple else 2 * self._num_units)

  @property
  def output_size(self):
    return self._num_units

  def __call__(self, inputs, state, scope=None):
    """Long short-term memory cell (LSTM)."""
    with tf.variable_scope(scope or type(self).__name__):
      # Parameters of gates are concatenated into one multiply for efficiency.
      if self._state_is_tuple:
        c, h = state
      else:
        c, h = tf.split(3, 2, state)
      concat = _convolve_linear([inputs, h], self.filter_size, self.features * 4, True)

      # i = input_gate, j = new_input, f = forget_gate, o = output_gate
      i, j, f, o = tf.split(3, 4, concat)

      new_c = (c * tf.nn.sigmoid(f + self._forget_bias) + tf.nn.sigmoid(i) *
               self._activation(j))
      new_h = self._activation(new_c) * tf.nn.sigmoid(o)

      if self._state_is_tuple:
        new_state = LSTMStateTuple(new_c, new_h)
      else:
        new_state = tf.concat(3, [new_c, new_h])
      return new_h, new_state

def _convolve_linear(args, filter_size, features, bias, bias_start=0.0, scope=None):
  """convolution:
  Args:
    args: 4D Tensor or list of 4D, batch x n, Tensors.
    filter_size: int tuple of filter with height and width.
    features: int, as number of features.
    bias_start: starting value to initialize bias; 0 by default.
    scope: VariableScope for created subgraph; defaults to "Linear".
  Returns:
    4D Tensor with shape [batch h w features]
  Raises:
    ValueError: if some of arguments have unspecified or wrong shape.
  """

  # Calculate total size of arguments on dimension 1.
  total_arg_size_depth = 0
  shapes = [a.get_shape().as_list() for a in args]
  for shape in shapes:
    if len(shape) != 4:
      raise ValueError("Linear needs 4D arguments: %s" % str(shapes))
    if not shape[3]:
      raise ValueError("Linear needs shape[4] of arguments: %s" % str(shapes))
    else:
      total_arg_size_depth += shape[3]

  dtype = [a.dtype for a in args][0]

  # Computation
  with tf.variable_scope(scope or "Conv"):
    mat = tf.get_variable(
        "Mat", [filter_size[0], filter_size[1], total_arg_size_depth, features], dtype=dtype)
    if len(args) == 1:
      res = tf.nn.conv2d(args[0], mat, strides=[1, 1, 1, 1], padding='SAME')
    else:
      res = tf.nn.conv2d(tf.concat(3, args), mat, strides=[1, 1, 1, 1], padding='SAME')
    if not bias:
      return res
    bias_term = tf.get_variable(
        "Bias", [features],
        dtype=dtype,
        initializer=tf.constant_initializer(
            bias_start, dtype=dtype))
  return res + bias_term

