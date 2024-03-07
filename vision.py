from openai import AsyncOpenAI
import base64
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI()


async def vision(query, which_img):

    with open(which_img, "rb") as image:
        encoded_string = base64.b64encode(image.read()).decode("utf-8")

    response = await client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_string}",
                        },
                    },
                ],
            }
        ],
        max_tokens=3000,
    )
    return response.choices[0].message.content
