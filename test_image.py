import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

image_path = r"C:\Users\JinA\Desktop\강진아자료\07] 교육자료\010] 강북여성인력개발센터\Vibe Coding 수업\project2_20260629\img\햄버거.jpeg"

with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="google/gemma-4-26b-a4b-it:free",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "이 이미지에 뭐가 보이는지 한국어로 설명해줘."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ],
        }
    ],
)

print(response.choices[0].message.content)
