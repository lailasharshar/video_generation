from dotenv import load_dotenv
import openai
import requests

load_dotenv()


# Function to generate an image using OpenAI - Tried this originally but wasn't crazy about the images
def generate_image(prompt, file_path, generic_prompt):
    response = openai.images.generate(
        model="dall-e-3",
        prompt=f'{prompt} {generic_prompt}',
        n=1,
        size="1024x1024"
    )
    print(response)

    # Get the image URL from the response
    image_url = response.data[0].url
    print(image_url)

    # Download the image from the URL
    image_data = requests.get(image_url).content

    # Save the image to a file
    with open(file_path, 'wb') as file:
        file.write(image_data)

    print(f"Image saved to {file_path}")






