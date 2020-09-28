"""
Composite Kernel Table image format
Bert Myroon
Started:  30 Aug, 2020
Released: 27 Sep, 2020

GNU GPL v3-0-or-later

Note:
    CKT (Composite Kernel Table) is a mostly "historic" name, as the original intent of this project is not what
    it turned out being. This program encodes any image as 24 (w*h)-bit numbers, where w and h are the image
    width and height, respectively. Originally, I wanted to make a form of image compression where the images
    would be broken up into kernels, which would then be each stored as an index out of a list of possible kernels
    given the image size. As it turns out, the very large numbers required to describe the index of these kernels take
    up exactly as much space as just storing the image as a bitmap. Makes sense if you think about it... whoops!

    Also, the file extension used by the program .kis stands for "kernel index sequence". The name is not strictly
    accurate anymore, but I don't care to change it.
"""

from sys import argv
from PIL import Image
import os.path

DEBUG = False
'''
Important offsets (decimal):
02-03: image size (bytes)
18-19: image width
22-23: image height
26-27: colour planes
28-29: colour depth (bits)
30-33: compression method (none)
34-37: image size (bytes)
'''

# Used for exporting encoded images as a bitmap
# Useful if you want to play with the encoded images before decoding
BITMAP_HEADER = \
    [
        0x42, 0x4d, 0xff, 0xff,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x7a, 0x00,
        0x00, 0x00, 0x6c, 0x00,
        0x00, 0x00, 0xff, 0xff,
        0x00, 0x00, 0xff, 0xff,
        0x00, 0x00, 0x01, 0x00,
        0x18, 0x00, 0x00, 0x00,
        0x00, 0x00, 0xff, 0xff,
        0xff, 0xff, 0xc3, 0x0e,
        0x00, 0x00, 0xc3, 0x0e,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x42, 0x47,
        0x52, 0x73, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x02, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00,
        0x00, 0x00
    ]

# File header used for .kis files
# The first three bytes are just 'CKT'
# The next four are the image width and height
CKT_HEADER = [
    0x43, 0x4b, 0x54,
    0xff, 0xff,
    0xff, 0xff
]


def validate_arguments(args):
    # Tries to catch errors with the user's arguments
    num_args = len(args)

    error = False

    try:
        # Make sure the number of arguments is good
        assert num_args == 5

    except AssertionError:
        error = "Wrong number of arguments"
        return error
    else:
        mode_arg = args[1]
        in_arg = args[2]
        out_arg = args[3]
        bitmap_or_reverse_arg = args[4]

    try:
        # Make sure a valid option is given
        assert mode_arg in ["encode", "decode"]

    except AssertionError:
        error = "Invalid option. Use 'encode' or 'decode'"

    try:
        # Make sure input file exists
        assert (os.path.isfile(in_arg))

    except AssertionError:
        error = "Given input file does not exist"

    try:
        # Make sure whether to output the image as a bitmap is true or false
        if num_args == 5:
            assert bitmap_or_reverse_arg in ["true", "false"]

    except AssertionError:
        error = "Final argument must be 'true' or 'false'"

    return error


def print_usage(error_msg):
    usage_msg = open("lib/usage.txt", "r").read()
    print(error_msg, '\n', usage_msg)


def main(args):
    # Debug mode was used by me during development
    # It won't be on for you, unless you change it in the code
    if not DEBUG:
        error = validate_arguments(args)
        if error:
            print_usage(error)
            return 1

        parse_and_run(args)

    else:
        print("WARNING: running in debug mode, problems may occur!"
              " This is likely a bug, contact the developer")
        debug_options = open("lib/debug_options.txt", "r").read().split('\n')
        args += debug_options
        print(args)
        parse_and_run(args)


def parse_and_run(args):
    # Runs the appropriate function based on user-provided arguments
    modes = {"encode": encode,
             "decode": decode}

    mode = args[1]
    in_arg = args[2]
    out_arg = args[3]
    bitmap_or_reverse_arg = ['false', 'true'].index(args[4].lower())
    used_args = [in_arg, out_arg, bitmap_or_reverse_arg]

    modes[mode](*used_args)


def encode(in_path, out_path, bitmap_arg):
    # Load in the input image
    in_img = Image.open(in_path)
    img_width = in_img.size[0]
    img_height = in_img.size[1]
    pixels = in_img.load()

    # Append the .kis (Kernel Index Sequence) file extension if needed
    if out_path[-4:] != ".kis":
        out_path += ".kis"

    rgb_indices = []
    # Index all the RGB values as a 24-bit int
    for x in range(img_width):
        for y in range(img_height):
            try:
                value = rgb_to_index(pixels[x, y])
            except TypeError:
                print("ERROR: Indexed-colour images are not supported. Convert to RGB and try again")
                return 1

            rgb_indices.append(value)

    # Split each 24-bit int to 24 1-bit ints
    split_rgb_indices = []
    for i in rgb_indices:
        bits = bin(i)[2:]
        bits = '0' * (24 - len(bits)) + bits  # Since we're working with 24-bit ints, we need to pad to 24 bits
        split_rgb_indices.append(bits)

    # Arrange the 24-bit ints into kernels. Originally this was supposed to be used for compression
    # What this really does is convert the 24-bit numbers into 24 (w*h)-bit numbers
    kernel = []
    kernels = []
    sub_i = 0
    while len(kernels) < 24:
        for split_rgb_index in split_rgb_indices:
            digit = split_rgb_index[sub_i]
            kernel.append(digit)

            if len(kernel) == len(split_rgb_indices):
                sub_i += 1
                kernels.append(kernel)
                kernel = []

    # Change the numbers from lists into strings
    numeric_kernels = []
    for kernel in kernels:
        kernel_val = ''
        for d in kernel:
            kernel_val += d

        numeric_kernels.append(kernel_val)

    # Prepare bytes for writing
    kernel_stream = ''.join(numeric_kernels)
    kernel_bytes = bytearray(int(kernel_stream, 2).to_bytes(len(kernel_stream) // 8, "little"))

    # I'm not sure why these are needed, but if you try to RE-encode a .kis bitmap without these, PIL complains
    # If PIL still gives you issues (truncated image), you will need to first convert .kis into a proper .bmp
    additional_bytes = bytes(img_height)

    hex_width = img_width.to_bytes(2, "little")
    hex_height = img_height.to_bytes(2, "little")
    if bitmap_arg:
        # Generate data for header
        image_length = len(kernel_bytes) + len(BITMAP_HEADER)
        hex_size = image_length.to_bytes(4, "little")

        # Write to header
        # BITMAP_HEADER[2] = hex_size[0]
        # BITMAP_HEADER[3] = hex_size[1]
        BITMAP_HEADER[18] = hex_width[0]
        BITMAP_HEADER[19] = hex_width[1]

        BITMAP_HEADER[22] = hex_height[0]
        BITMAP_HEADER[23] = hex_height[1]

        BITMAP_HEADER[34] = hex_size[0]
        BITMAP_HEADER[35] = hex_size[1]
        BITMAP_HEADER[36] = hex_size[2]
        BITMAP_HEADER[37] = hex_size[3]

        # Add header to file
        kernel_bytes.reverse()
        BITMAP_HEADER.reverse()
        kernel_bytes.extend(BITMAP_HEADER)
        kernel_bytes.reverse()
        kernel_bytes.extend(additional_bytes)

    else:
        # Create minimal header
        CKT_HEADER[3] = hex_width[0]
        CKT_HEADER[4] = hex_width[1]
        CKT_HEADER[5] = hex_height[0]
        CKT_HEADER[6] = hex_height[1]
        kernel_bytes.reverse()
        CKT_HEADER.reverse()
        kernel_bytes.extend(CKT_HEADER)
        kernel_bytes.reverse()

    # Write file
    output_file = open(out_path, 'wb')
    output_file.write(kernel_bytes)
    output_file.close()

    if DEBUG:
        print(len(rgb_indices), *rgb_indices)
        print(len(split_rgb_indices), *split_rgb_indices)
        print(len(kernels), *kernels)
        print(len(numeric_kernels), *numeric_kernels)


def decode(infile, outfile, reverse_arg):
    infile = open(infile, 'rb').read()

    # Detect if the file is saved as a bitmap, or .kis
    if infile[0:2].decode(errors="ignore") == "BM":
        print("Input file is a bitmap")
        # Get the image height
        img_width = infile[18] + 256 * infile[19]
        img_height = infile[22] + 256 * infile[23]

        # Remove the bitmap header
        infile = infile[len(BITMAP_HEADER):]

        # Remove the additional null bytes at the end added by the .kis bitmap encoder
        infile = infile[:-img_height]

    else:
        print("Input file is not a bitmap, is it a KIS?")
        img_width = infile[3] + 256 * infile[4]
        img_height = infile[5] + 256 * infile[6]

        # Remove the CKT header
        infile = infile[len(CKT_HEADER):]

    # Check to make sure decoding is possible
    if len(infile) != img_width * img_height * 3:
        print("ERROR: input file is not a Kernel Index Sequence image")
        print("Expected length", img_width*img_height*3, "got", len(infile))
        print("Attempt to truncate/pad input file? ")
        attempt_padding = input("If the expected size is very large, this should NOT be done. Likely you need to"\
                                "\n convert your image to .bmp before decoding.").lower()

        # Handle empty input
        if attempt_padding == '':
            attempt_padding = 'n'
        else:
            attempt_padding = attempt_padding[0]

        # Calculate how many bytes are missing/extra
        if attempt_padding == 'y':
            excess_bytes = len(infile) - img_width*img_height*3

            if excess_bytes < 1:
                # If bytes are missing, append null bytes
                infile = bytearray(infile)
                infile.extend(bytes(-excess_bytes))
            else:
                # If we have too many bytes, just remove them
                infile = infile[:-excess_bytes]

        else:
            print("Aborting")
            return 1
    else:
        # You are decoding an ordinary .kis, instead of causing schenanigans by decoding a non-encoded .bmp
        print("Input file is valid KIS")

    # Split the input bytes into a list of groups of bytes with length 1
    sublist_length = 1
    kernels_bytes = [infile[i: i + sublist_length] for i in range(0, len(infile), sublist_length)]

    # Convert the bytes into binary format
    kernels_bits = []
    for bs in kernels_bytes:
        bits = ''
        for b in bs:
            bits += bin(b)[2:]
            bits = '0' * (8 - len(bits)) + bits

        kernels_bits.append(bits)

    # This is counter-intuitive, but correct!
    # This reverse actually 'de-reverses' the bits so in reverse mode, we omit it
    if not reverse_arg:
        kernels_bits.reverse()

    # Group the bits into bytes
    kernels_joined_bits = ''
    for eight_bit_group in kernels_bits:
        kernels_joined_bits += eight_bit_group

    # Group the bits into groups of img_width*img_height
    sublist_length = img_width * img_height
    kernels_bits = [kernels_joined_bits[i: i + sublist_length] for i in
                    range(0, len(kernels_joined_bits) - sublist_length + 1, sublist_length)]

    # Convert the bytes from "kernel format" to RGB format
    rgb_binary = ''
    bits_index = 0
    for i in range(len(kernels_bits[0])):
        for bs in kernels_bits:
            rgb_binary += bs[bits_index]
        bits_index += 1

    # Split the rgb binary into groups of 24
    sublist_length = 24
    rgb_split_binary = [rgb_binary[i: i + sublist_length] for i in
                        range(0, len(rgb_binary) - sublist_length + 1, sublist_length)]

    # Convert from binary to base 10. This gives is our old RGB indices in int form
    rgb_indices = [int(b, 2) for b in rgb_split_binary]

    # Convert the rgb index numbers into rgb tuples
    rgb = []
    for rgbi in rgb_indices:
        rgb_bytes = rgbi.to_bytes(3, "big")
        rgb.append((rgb_bytes[0], rgb_bytes[1], rgb_bytes[2]))

    # Re-arrange the rgb values into the correct order
    reordered_rgb = [()] * len(rgb)
    for i in range(len(rgb)):
        # This looks nasty, but this effectively swaps the rows and columns of the image
        # I'm not sure why I need to do this, but presumably I messed up the order somewhere
        # during decoding, and fixing it this way is easier than locating where I messed up
        new_index = ((img_width * (i + 1) - (img_width - 1)) % len(rgb)) + (i // img_height)
        reordered_rgb[new_index - 1] = rgb[i]

    if DEBUG:
        print(len(kernels_bits), *kernels_bits)
        print(len(rgb_binary), rgb_binary)
        print(len(rgb_split_binary), rgb_split_binary)
        print(len(rgb_indices), rgb_indices)
        print(len(rgb), *rgb)
        print(len(reordered_rgb), reordered_rgb)

    # Append the .bmp file extension if needed
    if outfile[-4:] != ".bmp":
        outfile = outfile + ".bmp"

    # Write the decode image as a bmp
    output_image = Image.new("RGB", (img_width, img_height), 0)
    output_image.putdata(reordered_rgb)
    output_image.save(outfile)
    output_image.close()


def rgb_to_index(c):
    return 65536 * c[0] + 256 * c[1] + c[2]


if __name__ == '__main__':
    main(argv)
