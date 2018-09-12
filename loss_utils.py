import tensorflow as tf
import numpy as np
import tensorflow.contrib.slim as slim
import cv2

def average_gradients(tower_grads):
  """Calculate the average gradient for each shared variable across all towers.

  Note that this function provides a synchronization point across all towers.

  Args:
    tower_grads: List of lists of (gradient, variable) tuples. The outer list
      is over individual gradients. The inner list is over the gradient
      calculation for each tower.
  Returns:
     List of pairs of (gradient, variable) where the gradient has been averaged
     across all towers.
  """
  average_grads = []
  for grad_and_vars in zip(*tower_grads):
    # Note that each grad_and_vars looks like the following:
    #   ((grad0_gpu0, var0_gpu0), ... , (grad0_gpuN, var0_gpuN))
    grads = []
    for g, _ in grad_and_vars:
      # Add 0 dimension to the gradients to represent the tower.
      expanded_g = tf.expand_dims(g, 0)

      # Append on a 'tower' dimension which we will average over below.
      grads.append(expanded_g)

    # Average over the 'tower' dimension.
    grad = tf.concat(axis=0, values=grads)
    grad = tf.reduce_mean(grad, 0)

    # Keep in mind that the Variables are redundant because they are shared
    # across towers. So .. we will just return the first tower's pointer to
    # the Variable.
    v = grad_and_vars[0][1]
    grad_and_var = (grad, v)
    average_grads.append(grad_and_var)
  return average_grads

def mean_squared_error(true, pred):
  """L2 distance between tensors true and pred.

  Args:
    true: the ground truth image.
    pred: the predicted image.
  Returns:
    mean squared error between ground truth and predicted image.
  """
  return tf.reduce_sum(tf.square(true - pred)) / tf.to_float(tf.size(pred))

def mean_charb_error(true, pred, beta):
  return tf.reduce_sum(tf.sqrt((tf.square(beta*(true-pred)) + 0.001*0.001))) / tf.to_float(tf.size(pred))

def mean_charb_error_wmask(true, pred, mask, beta):
  return tf.reduce_sum(tf.sqrt((tf.square(beta*(true-pred)) + 0.001*0.001))*mask) / tf.to_float(tf.size(pred))


def weighted_mean_squared_error(true, pred, weight):
  """L2 distance between tensors true and pred.

  Args:
    true: the ground truth image.
    pred: the predicted image.
  Returns:
    mean squared error between ground truth and predicted image.
  """
  
  tmp = tf.reduce_sum(weight*tf.square(true-pred), axis=[1,2], keep_dims=True) / tf.reduce_sum(weight, axis=[1, 2], keep_dims=True)
  return tf.reduce_mean(tmp)
  #return tf.reduce_sum(tf.square(true - pred)*weight) / tf.to_float(tf.size(pred))
  #return tf.reduce_sum(tf.square(true - pred)*weight) / tf.reduce_sum(weight)

def mean_L1_error(true, pred):
  """L2 distance between tensors true and pred.

  Args:
    true: the ground truth image.
    pred: the predicted image.
  Returns:
    mean squared error between ground truth and predicted image.
  """
  return tf.reduce_sum(tf.abs(true - pred)) / tf.to_float(tf.size(pred))

def weighted_mean_L1_error(true, pred, weight):
  """L2 distance between tensors true and pred.

  Args:
    true: the ground truth image.
    pred: the predicted image.
  Returns:
    mean squared error between ground truth and predicted image.
  """
  return tf.reduce_sum(tf.abs(true - pred)*weight) / tf.to_float(tf.size(pred))

def gradient_x(img):
    gx = img[:,:,:-1,:] - img[:,:,1:,:]
    return gx

def gradient_y(img):
    gy = img[:,:-1,:,:] - img[:,1:,:,:]
    return gy

def cal_grad_error(flo, image, beta):
  """Calculate the gradient of the given image by calculate the difference between nearby pixels
  """
  error = 0.0
  img_grad_x = gradient_x(image)
  img_grad_y = gradient_y(image)
  
  weights_x = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_x), 3, keep_dims=True))
  weights_y = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_y), 3, keep_dims=True))
    
  #error += weighted_mean_L1_error(flo[:, 1:, :, :], flo[:, :-1, :, :], weights_y*beta)
  #error += weighted_mean_L1_error(flo[:, :, 1:, :], flo[:, :, :-1, :], weights_x*beta)
  
  error += mean_charb_error_wmask(flo[:, 1:, :, :], flo[:, :-1, :, :], weights_y, beta)
  error += mean_charb_error_wmask(flo[:, :, 1:, :], flo[:, :, :-1, :], weights_x, beta)

    
  return error / 2.0

def cal_grad2_error(flo, image, beta):
  def gradient(pred):
      D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
      D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
      return D_dx, D_dy
  img_grad_x, img_grad_y = gradient(image)
  weights_x = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_x), 3, keep_dims=True))
  weights_y = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_y), 3, keep_dims=True))
  
  dx, dy = gradient(flo)
  dx2, dxdy = gradient(dx)
  dydx, dy2 = gradient(dy)

  return (tf.reduce_mean(beta*weights_x[:,:, 1:, :]*tf.abs(dx2)) + \
         #tf.reduce_mean(beta*weights_x[:, 1:, :, :]*tf.abs(dxdy)) + \
         #tf.reduce_mean(beta*weights_y[:, :, 1:, :]*tf.abs(dydx)) + \
         tf.reduce_mean(beta*weights_y[:, 1:, :, :]*tf.abs(dy2))) / 2.0
         
def cal_grad2_error_mask(flo, image, beta, mask):
  def gradient(pred):
      D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
      D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
      return D_dx, D_dy
  img_grad_x, img_grad_y = gradient(image)
  weights_x = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_x), 3, keep_dims=True))
  weights_y = tf.exp(-10.0*tf.reduce_mean(tf.abs(img_grad_y), 3, keep_dims=True))
  
  dx, dy = gradient(flo)
  dx2, dxdy = gradient(dx)
  dydx, dy2 = gradient(dy)

  return (tf.reduce_mean(beta*weights_x[:,:, 1:, :]*tf.abs(dx2) * mask[:, :, 1:-1, :]) + \
         tf.reduce_mean(beta*weights_y[:, 1:, :, :]*tf.abs(dy2) * mask[:, 1:-1, :, :])) / 2.0
         
         
def cal_grad2_error_seg(flo, seg, beta):
  def gradient(pred):
      D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
      D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
      return D_dx, D_dy
  
  weights_x = 1.0 - seg[:, :, 1:, :]
  weights_y = 1.0 - seg[:, 1:, :, :]
  
  dx, dy = gradient(flo)
  dx2, dxdy = gradient(dx)
  dydx, dy2 = gradient(dy)

  return (tf.reduce_mean(beta*weights_x[:,:, 1:, :]*tf.abs(dx2)) + \
         #tf.reduce_mean(beta*weights_x[:, 1:, :, :]*tf.abs(dxdy)) + \
         #tf.reduce_mean(beta*weights_y[:, :, 1:, :]*tf.abs(dydx)) + \
         tf.reduce_mean(beta*weights_y[:, 1:, :, :]*tf.abs(dy2))) / 2.0

def img_grad_error(true, pred, mask, beta):
  error = 0.0
  
  error += mean_charb_error_wmask(true[:, 1:, :, :] - true[:, :-1, :, :], 
                            pred[:, 1:, :, :] - pred[:, :-1, :, :], mask[:, 1:, :, :], beta)
  error += mean_charb_error_wmask(true[:, :, 1:, :] - true[:, :, :-1, :], 
                            pred[:, :, 1:, :] - pred[:, :, :-1, :], mask[:, :, 1:, :], beta)
  
  return error / 2.0
  

def cal_epe(flo1, flo2):
  return tf.reduce_mean(tf.sqrt(tf.reduce_sum(tf.square(flo1 - flo2), axis=3)))

def get_image_grad(image, scale = 1.0):
  image_pad = tf.pad(image, [[0,0], [1,1], [1,1],[0,0]], "SYMMETRIC")
  return tf.concat([image, 
                    (image - image_pad[:, 1:-1, 0:-2, :]) * scale, 
                    (image - image_pad[:, 1:-1, 2:, :]) * scale,
                    (image - image_pad[:, 0:-2, 1:-1, :]) * scale,
                    (image - image_pad[:, 2:, 1:-1, :]) * scale, 
                    (image - image_pad[:, 0:-2, 0:-2, :]) * scale,
                    (image - image_pad[:, 0:-2, 2:, :]) * scale,
                    (image - image_pad[:, 2:, 0:-2, :]) * scale,
                    (image - image_pad[:, 2:, 2:, :]) * scale], axis=3)

def get_image_grad2(image):
  batch_size, img_height, img_width, color_channels = map(int, image.get_shape()[0:4])
  
  image_pad = tf.pad(image, [[0,0], [2,2], [2,2],[0,0]], "SYMMETRIC")
  
  grads = []
  for i in range(5):
    for j in range(5):
      if i != 2 or j != 2:
        grads.append(image - image_pad[:, i:(i+img_height), j:(j+img_width), :])
  
  return tf.concat([image] + grads, axis = 3)

  
def get_channel(image):
  zeros = tf.zeros_like(image)
  ones = tf.ones_like(image)
  
  #gray = 0.21*image[:, :, :, 0] + 0.72*image[:, :, :, 1] + 0.07*image[:, :, :, 2]
  channels = []
  for i in range(10):
    channels.append(tf.where(tf.logical_and(image >= i/10.0, image < (i+1)/10.0), ones, zeros))
  
  return tf.concat([image]+channels, axis=3)


def get_reference_explain_mask(downscaling, opt):
    tmp = np.array([0,1])
    ref_exp_mask = np.tile(tmp, 
                           (opt.batch_size // opt.num_gpus, 
                            int(opt.img_height/(2**downscaling)), 
                            int(opt.img_width/(2**downscaling)), 
                            1))
    ref_exp_mask = tf.constant(ref_exp_mask, dtype=tf.float32)
    return ref_exp_mask

def compute_smooth_loss(pred_disp):
    def gradient(pred):
        D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
        D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
        return D_dx, D_dy
    dx, dy = gradient(pred_disp)
    dx2, dxdy = gradient(dx)
    dydx, dy2 = gradient(dy)
    return tf.reduce_mean(tf.abs(dx2)) + \
           tf.reduce_mean(tf.abs(dxdy)) + \
           tf.reduce_mean(tf.abs(dydx)) + \
           tf.reduce_mean(tf.abs(dy2))

def compute_smooth_loss_wedge(disp, edge, mode='l1', alpha=10.0):
    ## in edge, 1 represents edge, disp and edge are rank 3 vars

    def gradient(pred):
        D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
        D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
        return D_dx, D_dy

    disp_grad_x, disp_grad_y = gradient(disp)
    dx2, dxdy = gradient(disp_grad_x)
    dydx, dy2 = gradient(disp_grad_y)

    # edge_grad_x, edge_grad_y = gradient(edge)
    weight_x = tf.exp(-1*alpha*tf.abs(edge))
    weight_y = tf.exp(-1*alpha*tf.abs(edge))

    if mode == "l2":
        smoothness_loss = tf.reduce_mean(tf.clip_by_value(dx2 * weight_x[:,:,1:-1,:], 0.0, 10.0)) + \
                      tf.reduce_mean(tf.clip_by_value(dy2 * weight_y[:,1:-1,:,:], 0.0, 10.0)) #+ \
    if mode == "l1":
        smoothness_loss = tf.reduce_mean(tf.abs(disp_grad_x * weight_x[:,:,1:,:])) + \
                      tf.reduce_mean(tf.abs(disp_grad_y * weight_y[:,1:,:,:]))

    return smoothness_loss

def compute_edge_aware_smooth_loss_1st(disp, image):
  def gradient(pred):
      D_dy = pred[:, 1:, :, :] - pred[:, :-1, :, :]
      D_dx = pred[:, :, 1:, :] - pred[:, :, :-1, :]
      return D_dx, D_dy
  disp_gradients_x, disp_gradients_y = gradient(disp)
  image_gradients_x, image_gradients_y = gradient(image)

  weights_x = tf.exp(-10.0*tf.reduce_mean(tf.abs(image_gradients_x), 3, keep_dims=True))
  weights_y = tf.exp(-10.0*tf.reduce_mean(tf.abs(image_gradients_y), 3, keep_dims=True))

  smoothness_dx = disp_gradients_x * weights_x
  smoothness_dy = disp_gradients_y * weights_y

  smoothness_loss = tf.reduce_mean(tf.abs(smoothness_dx)) + \
                    tf.reduce_mean(tf.abs(smoothness_dy))
  return smoothness_loss

def SSIM(x, y):
    C1 = 0.01 ** 2
    C2 = 0.03 ** 2

    mu_x = slim.avg_pool2d(x, 3, 1, 'VALID')
    mu_y = slim.avg_pool2d(y, 3, 1, 'VALID')

    sigma_x  = slim.avg_pool2d(x ** 2, 3, 1, 'VALID') - mu_x ** 2
    sigma_y  = slim.avg_pool2d(y ** 2, 3, 1, 'VALID') - mu_y ** 2
    sigma_xy = slim.avg_pool2d(x * y , 3, 1, 'VALID') - mu_x * mu_y

    SSIM_n = (2 * mu_x * mu_y + C1) * (2 * sigma_xy + C2)
    SSIM_d = (mu_x ** 2 + mu_y ** 2 + C1) * (sigma_x + sigma_y + C2)

    SSIM = SSIM_n / SSIM_d

    return tf.clip_by_value((1 - SSIM) / 2, 0, 1)
  
def deprocess_image(image):
  # Assuming input image is float32
  return tf.image.convert_image_dtype(image, dtype=tf.uint8)

def preprocess_image(image):
  # Assuming input image is uint8
  image = tf.image.convert_image_dtype(image, dtype=tf.float32)
  return image

def compute_exp_reg_loss(pred, ref):
  l = tf.nn.softmax_cross_entropy_with_logits(
      labels=tf.reshape(ref, [-1, 2]),
      logits=tf.reshape(pred, [-1, 2]))
  return tf.reduce_mean(l)

def hisEqulColor(img):
  ycrcb=cv2.cvtColor(img,cv2.COLOR_BGR2YCR_CB)
  channels=cv2.split(ycrcb)
  cv2.equalizeHist(channels[0],channels[0])
  cv2.merge(channels,ycrcb)
  cv2.cvtColor(ycrcb,cv2.COLOR_YCR_CB2BGR,img)
  return img

def charbonnier_loss(x, mask=None, truncate=None, alpha=0.45, beta=1.0, epsilon=0.001):
    """Compute the generalized charbonnier loss of the difference tensor x.
    All positions where mask == 0 are not taken into account.
    Args:
        x: a tensor of shape [num_batch, height, width, channels].
        mask: a mask of shape [num_batch, height, width, mask_channels],
            where mask channels must be either 1 or the same number as
            the number of channels of x. Entries should be 0 or 1.
    Returns:
        loss as tf.float32
    """
    batch, height, width, channels = tf.unstack(tf.shape(x))
    normalization = tf.cast(batch * height * width * channels, tf.float32)

    error = tf.pow(tf.square(x * beta) + tf.square(epsilon), alpha)

    if mask is not None:
        error = tf.multiply(mask, error)

    if truncate is not None:
        error = tf.minimum(error, truncate)

    return tf.reduce_sum(error) / normalization