import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b:free",
    messages=[
        {"role": "user", "content": "대한민국의 수도는 어디야? 한 문장으로만 답해줘."}
    ],
)

print(response.choices[0].message.content)
