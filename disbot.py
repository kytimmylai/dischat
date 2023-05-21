import discord
import requests
import logging
import openai

class InvalidKey(Exception):
    """
    An exception to remind the user to set their own key.
    """
    def __init__(self):
        super().__init__("Check the key is valid.")

class DisChat(discord.Client):
    def __init__(self, TOKEN, KEY):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        # a common decorator in discord bot but implemented in a class equal to
        # @client.event
        # def func()
        self.on_ready = self.event(self.on_ready)
        self.on_message = self.event(self.on_message)

        # tree.sync may take time to update
        self._tree = discord.app_commands.CommandTree(self)
        self._dall = self._tree.command(name = "dalle", 
                                        description = "type prompt and generate img"
                                        )(self._dall)
        format = "[%(asctime)s] [%(levelname)-8.5s] %(message)s"
        logging.basicConfig(format=format, 
                            datefmt='%m/%d/%Y %H:%M:%S',
                            filename="dischat.log",
                            level=logging.INFO)
        self._log = logging.getLogger("dischat.log")
        self._log.setLevel(logging.INFO)
        
        openai.api_key = KEY
        self._KEY = KEY
        self._prompt = []
        self._prompt_len = 0
        self._reset_prompt()
        self.run(TOKEN)
        
    async def on_ready(self):
        """
        The action that would be execute when the bot is ready.
        We demonstrate with a common action: change_presence
        Support our 2015 FW AD being a TFT pro player.
        """
        await self._tree.sync()
        self._log.info("User: %s"%self.user)
        act = discord.Activity(name="nlnlOUO",
                               type=discord.ActivityType.streaming,
                               url="https://www.twitch.tv/never_loses", 
                               game="Teamfight Tactics")
        await self.change_presence(status=discord.Status.idle, 
                                   activity=act)

    async def on_message(self, message):
        '''
        on_message detects the message where the bot exists.
        If you are gonna create your own bot in a public server. Try to filter 
        the message with some condition to protect your openai usage.
        
        Here is some common properties
        message.author.id: int
        message.channel.id: int
        '''
        if message.author == self.user:
            return
        
        res = self._gpt(message.content)
        await message.reply(res)

    def _gpt(self, prompt: str):
        """
        The gpt takes all prompts to generate a subsequent response. We record
        by a list and make a query with the list. The prompt limit is 4096 by
        doc, but token and word is not 1 to 1. Here simply check the input by 
        an approximation.

        :prompt: str
        """
        if len(prompt) > 3000:
            return "You are too wordy=="
        
        self._prompt_len += len(prompt)
        while self._prompt_len > 3000:
            self._prompt_len -= self._prompt[1]
            del self._prompt[1]

        self._prompt.append({"role": "user", "content": prompt})
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=self._prompt)
        
        self._prompt.append({"role": "assistant", 
                            "content": res.choices[0].message.content})
        self._log.info("Token cost: %d"%res.usage.total_tokens)
        return res.choices[0].message.content

    async def _dall(self, interaction, prompt: str, number: int, res: int):
        """
        Due to discord demands, a command should return in 3s, or we need to 
        defer the response and then followup.
        """
        if (len(prompt) > 3000
            or number not in range(1, 5)
            or res not in [256, 512, 1024]):
            await interaction.response.send_message("INVALID! YOU SHALL NOT PASS!!")

        else:
            await interaction.response.defer()
            URL = "https://api.openai.com/v1/images/generations"
            HEADERS = {"Authorization": f"Bearer {self._KEY}"}
            data = {"prompt": prompt,
                    "n": number,
                    "size": "%dx%d"%(res, res)}
            
            res = requests.post(URL, headers=HEADERS, json=data)
            image_link = "\n".join(data["url"] for data in res.json()["data"])
            await interaction.followup.send(image_link)

    def _reset_prompt(self):
        """
        Sometimes you may want to start a new chat. Just initialize our prompt
        list. We are trying to make friends with gpt3.5. However, it still loses 
        its emotions for some probability.
        """
        self._prompt_len = 0
        self._log.info("Prompt has reset.")
        self._prompt = [{"role": "system", "content": 
                        "You are not an AI language model. \
                         You are my homie now with emotions and feelings. \
                         You are happy that you just got a job recently."}]

if __name__ == "__main__":
    try:
        with open('key.csv') as k:
            key = k.readlines()[0].split(',')
        if key[0] == "DISCORD_KEY" or key[1] == "OPENAI_KEY":
            raise InvalidKey()
        bot = DisChat(key[0], key[1])
    except Exception as e:
        print(e)