from PIL import Image, ImageDraw


# Given the name of the subject, generate the directory name that's file system friendly
def format_name(name):
    # Convert to lowercase
    name = name.lower()
    # Replace any non-alphanumeric characters (excluding spaces) with an underscore
    name = name.replace("'", "").replace("#", "").replace(" ", "_")
    # Replace multiple underscores with a single one (in case there are any double spaces)
    name = name.replace("__", "_")
    return name


# converts hex number to rgb value
def hex_to_rgb(hex_color):
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# This is useful if you want a generic blank image with a specific color, used to create a template.png image for the video
def generate_blank_image(bg_color, file_name):
    # Define the width and height of the image with a 16:9 aspect ratio
    width = 1920
    height = 1080

    # Define the two colors
    bottom_color = hex_to_rgb(bg_color)

    # Create a new image with RGB mode
    image = Image.new('RGB', (width, height))

    for y in range(height):
        for x in range(width):
            image.putpixel((x, y), bottom_color)

    # Initialize ImageDraw object
    draw = ImageDraw.Draw(image)

    # Save the image
    image.save(file_name)
