
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
      tensor with shape '[batch_size x shape[0] x shape[1] x (features*2)]
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

  def __init__(self, shape, filter, features, forget_bias=1.0, input_size=None,
               state_is_tuple=False, activation=tf.nn.tanh):
    """Initialize the basic CLSTM cell.
    Args:
      shape: int tuple of the height and width of the cell
      filter: int tuple of the height and width of the filter
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
    self.filter = filter
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
    # inputs: batchsize x clstmshape x clstmshape x clstmfeatures
    with tf.variable_scope(scope or type(self).__name__):
      # Parameters of gates are concatenated into one multiply for efficiency.
      if self._state_is_tuple:
        c, h = state
      else:
        # c and h are each batchsize x clstmshape x clstmshape x clstmfeatures
        c, h = tf.split(state, 2, 3)
      # [inputs,h] is: 2 x batchsize x clstmshape x clstmshape x clstmfeatures

      doclstm=1
      if doclstm==1:
        concat = _convolve_linear([inputs, h], self.filter, self.features * 4, True)
        # http://colah.github.io/posts/2015-08-Understanding-LSTMs/
        # i = input_gate, j = new_input, f = forget_gate, o = output_gate (each with clstmfeatures features)
        i, j, f, o = tf.split(concat, 4, 3)
      else:
        # work in-progress
        incat = tf.concat(args,3)
        # general W.x + b separately for each i,j,f,o
        #i = tf.matmul(incat,weightsi) + biasesi
        #j = tf.matmul(incat,weightsj) + biasesj
        #f = tf.matmul(incat,weightsf) + biasesf
        #o = tf.matmul(incat,weightso) + biaseso
        
      # concat: batchsize x clstmshape x clstmshape x (clstmfeatures*4)


      new_c = (c * tf.nn.sigmoid(f + self._forget_bias) + tf.nn.sigmoid(i) *
               self._activation(j))
      new_h = self._activation(new_c) * tf.nn.sigmoid(o)

      if self._state_is_tuple:
        new_state = LSTMStateTuple(new_c, new_h)
      else:
        new_state = tf.concat([new_c, new_h],3)
      return new_h, new_state

def _convolve_linear(args, filter, features, bias, bias_start=0.0, scope=None):
  """convolution:
  Args:
    args: 4D Tensor or list of 4D, batch x n, Tensors.
    filter: int tuple of filter with height and width.
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
    # ensure each term in arg is exactly 4D
    if len(shape) != 4:
      raise ValueError("Linear needs 4D arguments: %s" % str(shapes))
    # ensure each term in arg has non-None 4D term
    if not shape[3]:
      raise ValueError("Linear needs shape[4] of arguments: %s" % str(shapes))
    else:
      # add last dimension (features) together
      total_arg_size_depth += shape[3]

  dtype = [a.dtype for a in args][0]

  # Computation
  with tf.variable_scope(scope or "Conv"):
    # setup weights as kernel x kernel x (input features = clstmfeatures*2) x (new features=clstmfeatures*4)
    mat = tf.get_variable(
        "Mat", [filter[0], filter[1], total_arg_size_depth, features], dtype=dtype)
    if len(args) == 1:
      res = tf.nn.conv2d(args[0], mat, strides=[1, 1, 1, 1], padding='SAME')
    else:
      # first argument is batchsize x clstmshape x clstmshape x (2*clstmfeatures)
      res = tf.nn.conv2d(tf.concat(args,3), mat, strides=[1, 1, 1, 1], padding='SAME')
      # res: batchsize x clstmshape x clstmshape x (clstmfeatures*4)
    if not bias:
      return res
    bias_term = tf.get_variable(
        "Bias", [features],
        dtype=dtype,
        initializer=tf.constant_initializer(
            bias_start, dtype=dtype))
  return res + bias_term

