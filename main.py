from g4f.client import Client


client = Client()
mass = ['кто такой человек','что ты умеешь','как тебя зовут']
for i in range(3):
    response = client.chat.completions.create(
        model='gpt-4.1',
        messages=[{'role': 'user', 'content':f'{mass[i]}'}],
        web_search=False
    )
    print(response.choices[0].message.content.replace('\n', ' '))