
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from deepclo.utils import configure_logger, show_images

try:
    from deepclo.core.syllabus import ImageHelper as IMPLOT, ConfigureLogger
    from deepclo.core.syllabus import Measure
    from curriculum_factory import reconstruct_from_patches
    from deepclo.core.syllabus import endlog, log
except (Exception, ImportError) as error:
    from deepclo.core.measures.measure_functions import Measure
    from curriculum_factory import reconstruct_from_patches
    from deepclo.timer import endlog, log


_logger = configure_logger(__file__, __name__, console=True)


def _patchify_tf(image_data, ksize_rows, ksize_cols, strides_rows, strides_cols,
                 rates=[1, 1, 1, 1], padding='VALID'):
    """[summary]

    Arguments:
        image_data {tftensor} -- Read image into byes the follow by tf.image.decode_image
        ksize_rows {pixels} -- height of sliding windows  
        ksize_cols {pixels} -- width of sliding window 
        strides_rows {pixels} -- vertical distance between centers of two consecutive patches 
        strides_cols {pixels} -- horizontal distance between centers of two consecutive patches 

    Keyword Arguments:
        rates {list} -- [description] (default: {[1, 1, 1, 1]})
        padding {string} -- [description] (default: {'SAME'})
    """
    # The size of sliding window
    ksizes = [1, ksize_rows, ksize_cols, 1]

    # How far the centers of 2 consecutive patches are in the image
    strides = [1, strides_rows, strides_cols, 1]

    image = tf.expand_dims(image_data, 0)
    image_patches = tf.extract_image_patches(
        image, ksizes, strides, rates, padding)

    return image_patches


def generate_patches_v2(image, input_h, input_w, patch_h, patch_w, pad=False, debug=False):
    """
    Splits an image into patches of size patch_h x patch_w
    Input: image of shape [image_h, image_w, image_ch]
    Output: batch of patches shape [n, patch_h, patch_w, image_ch]

    Arguments:
        image_string {sample} -- input string 
        input_h {pixels} -- input height in pixels 
        input_w {pixels} -- input width in pixels 
        patch_h {pixels} -- patch height to extract 
        patch_w {pixels} -- patch width to extract 
    """

    _logger.debug("Entering generate_patches_v2, image: ({},{}), patch: ({},{})".format(
        input_h, input_w, patch_h, patch_w))

    if debug:
        _logger.debug("Decoding image for debugging ...")
        image = tf.image.decode_image(image, channels=3, dtype=tf.float32)

    # assert image.shape.ndims == 3, _logger.error(
    #     "Assertion failed, image channel != 3")

    image = tf.reshape(image, [input_h, input_w, 3])

    padding = [[0, 0], [0, 0]]
    image_h = image.shape[0].value
    image_w = image.shape[1].value
    image_ch = image.shape[2].value
    p_area = patch_h * patch_w

    assert image_h == image_w and patch_h == patch_w, _logger.error(
        "Traning sample and patches must be of square size!")

    patches = None

    if pad:
        _logger.debug("Creating patches with [0] padding ...")
        patches = tf.space_to_batch_nd([image], [patch_h, patch_w], padding)
    else:
        _logger.debug("Creating patches ...")
        patches = tf.space_to_batch_nd([image], [patch_h, patch_w], padding)
    patches = tf.split(patches, p_area, 0)
    patches = tf.stack(patches, 3)
    patches = tf.reshape(patches, [-1, patch_h, patch_w, image_ch])

    _logger.debug("Successfully generated patches ")

    return patches


def image_data_conserved(original, reconstructed):
    return tf.reduce_all(tf.math.equal(original, reconstructed))


def reconstruction_conserves_data(original, reconstructed):
    return np.all(np.equal(original, reconstructed))


def p_por(image, height, width, measure, ordering, patch_h, patch_w):
    assert patch_h == patch_w, "CC V2 only supports equal sized patches!"
    patches = generate_patches_v2(image, height, width, patch_h, patch_w)
    reconstructed = reconstruct_from_patches(
        patches, height, width, measure=measure, ordering=ordering)

    return reconstructed


def test():
    image_file = '../samples/husky.jpg'
    patch_width = 56
    patch_height = 56
    input_size = (224, 224)

    assert patch_height == patch_width, "CC doesn't support different sized patches!"

    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
                                          log_device_placement=False)) as sess:

        image_string = tf.gfile.FastGFile(image_file, 'rb').read()

        patches = generate_patches_v2(
            image_string, input_size[0], input_size[1], patch_width, patch_height, debug=True)

        ssim = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.SSIM)
        kl = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.KL)
        psnr = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.PSNR)
        entropy = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.ENTROPY)
        mi = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.MI)
        ce = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.CE)
        l1 = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.L1)
        l2 = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.L2)
        max = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.MAX_NORM)
        je = reconstruct_from_patches(
            patches, input_size[0], input_size[1], measure=Measure.JE)

        # # assert original.shape == reconstructed.shape, "Reconstruction data loss, skipping sample"
        reconstructed_samples = [kl.eval(),
                                 mi.eval(), ce.eval(),
                                 l1.eval(), l2.eval(), max.eval(), je.eval(),
                                 entropy.eval(), ssim.eval(), psnr.eval()]

        titles = ["KL", "MI", "CE", "L1",
                  "L2", "MAX", "JE", "Entropy",
                  "SSIM", "PSNR"]
        plotter = IMPLOT()
        fig = show_images(reconstructed_samples, 2, titles=titles)
        plt.show()


if __name__ == '__main__':
    test()
