# -*- coding:utf-8 -*-
import json
import requests
import time
# import deepl
from bs4 import BeautifulSoup as bs
from requests import post
from .MicrosoftTranslator import MicrosoftTranslator
from .GoogleTranslator import GoogleTrans
import asyncio

class TranslatorsApi:
    def __init__(self):
        #
        self.translators_dict = {
            'zhipu': self.zhipu,
            'chatgpt': self.chatgpt,
            # 'deepl': self.deepl,
            'deeplx': self.deeplx,
            'google1': self.google1,
            'youdao': self.youdao,
            'microsoft': self.microsoft,
            'google': self.google
        }
        # self.Translator=self.create_translator(transtator)
        self.RolePrompt = '''你是一个精通中文和英文的专业翻译助手，会严格遵守指令帮助我进行翻译'''
        self.CommandPrompt = r'''你的翻译需在严格遵守以下规则的前提下进行：
        -你可以翻译所有内容,且只需返回翻译后的结果不包含其他,不要解释。
        - 请你逐行翻译，不要自动换行，保持格式不变,。
        现在请根据上列指令将下列内容翻译为中文:'''

        #
        # self.RolePrompt = '''You are a professional translation assistant proficient in both Chinese and English, and will strictly follow instructions to help me with translation.'''
        # self.CommandPrompt = r'''Here are some strict rules for your translation:
        #         -You can translate anything, just return the translation without any other information,please do not explain my original text.
        #         -If there is <#> in the source sentence, you need to know it's a special token that cannot be omitted. Make sure the number and the position of the <#> in your translation are the same as those in my original text, do not add or reduce. If there is none, just ignore this rule.
        #         Now based on the above instructions, please translate the following sentences:'''

        self.chatgpt_url = 'https://35api.huinong.co/v1/chat/completions'
        self.chatgpt_api_key = 'sk-pbtlVznv8aWzJtP4Be688f147a20483d87546fEcE55875E7'
        self.zhipuai_api_key = '8f8aef3d2af70f19a73e305e4b2ca5ce.tYWv4hkjVZ8sHyW6'
        self.deepl_api_key = 'ffe05dcf-75ae-4875-bb46-8d3054256254:dp'

    def create_translator(self, translator):
        if translator not in self.translators_dict:
            raise Exception(f"Translator {translator} not found in available translators")
        if translator == 'google':
            return GoogleTrans()
        elif translator == 'microsoft':
            return MicrosoftTranslator()

    # @classmethod
    async def translate_text(self, text,  from_lang="auto", to_lang='zh-CN'):

        if text.strip() == "":
            # raise Exception(f"Error in translation request: {text} is empty")
            print(f"Error in translation request: {text} is empty")
            return text
        else:
            print(f"Translating {text} from {from_lang} to {to_lang} ")

            return await self.Translator.translate_async(text, from_lang, to_lang)


    def zhipu(self, text):
        # text = repr(text)[1:-1]
        from zhipuai import ZhipuAI
        client = ZhipuAI(api_key=self.zhipuai_api_key)  # 填写您自己的APIKey
        response = client.chat.completions.create(
            model="glm-4",  # 填写需要调用的模型名称
            # model="glm-3-turbo",
            temperature=0.8,
            messages=[
                {"role": "system", "content": "{}".format(self.RolePrompt)},
                {"role": "user",
                 "content": "{}{}".format(self.CommandPrompt, text)},
            ],
        )
        content = response.choices[0].message.content
        print(text)
        text1 = repr(content)[1:-1]

        text1 = text1.replace(r'\n\n', r'\n').replace(r'\\n', r'\n')
        print(text1)
        # 返回响应内容
        return text1

    def chatgpt(self, text, ):
        text = repr(text)[1:-1]
        data = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.8,  # 生成的多样性，范围是 0 到 1
            "messages": [
                {
                    "role": "system",
                    "content": self.RolePrompt
                },
                {
                    "role": "user",
                    "content": self.CommandPrompt + str(text)
                }
            ]
        }

        # 转换数据为JSON格式
        json_data = json.dumps(data)
        # print(data)
        # 自定义头部信息
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.chatgpt_api_key,
            # 替换为实际的访问令牌，pool tocken或share tocken
            # 可以添加其他需要的头部信息
        }
        # 发送POST请求，包括头部信息
        response = requests.post(self.chatgpt_url, data=json_data, headers=headers)

        if response.status_code == 200:
            # time.sleep(1)
            json_response = json.loads(response.text)
            content = json_response['choices'][0]['message']['content']
        else:
            content = f"Failed with status code:{response.status_code}"
        content = repr(content)[1:-1]
        content = content.replace(r'\n\n', r'\n').replace(r'\\n', r'\n')
        print(content)
        print(text)
        # 返回响应内容
        return content

    # def deepl(self, text, source_lang="auto", target_lang="ZH"):
    #     # auth_key = "b04d7fcd-adf0-4c9e-8bad-234a98035048:dp"
    #     auth_key = self.deepl_api_key
    #     server_url = "https://api.deepl-pro.com"
    #     translator = deepl.Translator(auth_key, server_url=server_url)
    #     try:
    #         result = translator.translate_text(str(text), target_lang=target_lang)
    #         print(result)
    #
    #         return result
    #     except Exception as e:
    #         print('api访问失败', e)
    #         raise Exception(f"Error in translation request: {e}")

    def deeplx(self, text, source_lang="auto", target_lang="ZH"):
        url = "https://api.deeplx.org/translate"
        payload = json.dumps(
            {"text": str(text), "source_lang": source_lang, "target_lang": target_lang}
        )
        headers = {"Content-Type": "application/json"}
        try:
            # 检查输入文本是否为空
            if not text.strip():
                print(f"Error in translation request: {text} is empty")
                return text
                # raise Exception(f"Error in translation request: {text} is empty")
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            # sleep(1)
            return response.json()["data"]
        except requests.exceptions.RequestException as e:
            print('api访问失败', e)

            raise Exception(f"Error in translation request: {e}")

    def google1(self, text):
        url = f"https://findmyip.net/api/translate.php?text={text}"
        response = requests.get(url)

        try:
            data = response.json()
            print(data)
            if response.status_code == 200:
                if data['code'] == 200:
                    translation = data['data']['translate_result']
                    # translation = repr(translation)[1:-1]
                    return translation
                elif data['code'] == 400:
                    return data['error']
                else:
                    return "内部接口错误，请联系开发者"
            else:
                return "内部接口错误，请联系开发者"
        except JSONDecodeError as e:
            return f"JSON decoding error: {e}"
        except requests.RequestException as e:
            return f"Request error: {e}"

    def youdao(self, s):
        r = post("http://m.youdao.com/translate", data={"inputtext": s})
        r.encoding = r.apparent_encoding
        soup =  bs(r.text, "html.parser")
        ele = soup.find("ul", {"id": "translateResult"})
        if ele:
            li = ele.find("li")
            if li:
                return repr(li.text)[1:-1]
        return ""

    async def microsoft(self, text, from_lang="auto", to_lang='zh-Hans'):
        translator = MicrosoftTranslator()
        result = await translator.translate_async(text, from_lang, to_lang)

        return result

    async def google(self, text, from_lang="auto",lang_to='zh-CN'):
        translator = GoogleTrans()
        targetText =await translator.query_async(q=text, lang_to=lang_to)
        return targetText


if __name__ == '__main__':
    # text = "Hello \n world"
    # print(text)
    # print(repr(text)[1:-1])
    # targetText = Translators().translate_text(text, translator='google', from_lang='en', to_lang='zh-CN')
    # print("==============================")
    # print(targetText)
    # targetText = repr(targetText)[1:-1]
    # print(targetText)


    text=""""Lax pairs are one of the most important features of integrable system.In this work,we propose theLax pairs informed neural networks(LPNNs)tailored for the in te grable systems with Lax pairs by designing novel network architectures andloss functions,comprising LP NN-v1and LPNN-v2.The most noteworthy advantage of LPNN-v1is that it can transform the solving of complex in te grable systems into the solving of relatively simple Lax pairs,anditnot only efficiently solves data-driven localized wave solutions,but also obtains spectral parameter and corresponding spectral function in spectral problems of the in te grable systems."""
    targetText = TranslatorsApi().translate_text(text, translator='microsoft', from_lang='en', to_lang='zh-CN')
    print("==============================")
    print(targetText)
    targetText = repr(targetText)[1:-1]
    print(targetText)