import discord
from discord import app_commands
from discord.ext import commands

from youtube_dl import YoutubeDL


class OwnerButton(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
        self.timeout = 600

        button_url = discord.ui.Button(label="Conheça o desenvolvedor do bot",
                                       url="https://www.linkedin.com/in/lucasalazar/")
        self.add_item(button_url)


# class Dropdown(discord.ui.Select):
#     def __init__(self, songs: any, music_player):
#         options = [
#             discord.SelectOption(label='1', description=songs[0]['title'], emoji='🟥'),
#             discord.SelectOption(label='2', description=songs[1]['title'], emoji='🟩'),
#             discord.SelectOption(label='3', description=songs[2]['title'], emoji='🟦'),
#         ]
#
#         super().__init__(placeholder='Selecione a música que deseja', min_values=1,
#                          max_values=1, options=options)
#
#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.send_message(f'Você selecionou a música {self.values[0]}')
#
# class DropdownView(discord.ui.View):
#     def __init__(self, songs: any, music_player):
#         super().__init__()
#         self.add_item(Dropdown(songs, music_player))


class MusicPlayer(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.is_playing_song = False
        self.music_queue = []
        self.current_song = ""
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                               'options': '-vn'}
        self.voice_channel = ""

    def search_youtube_music(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                if item.startswith('http'):
                    song_list = ydl.extract_info(item, download=False)['entries']
                else:
                    song_list = ydl.extract_info(f"ytsearch:{item}", download=False)['entries']
            except Exception:
                return False

        # if len(song_list) > 1 and not item.startswith('http'):
        #     return [{'source': song_list[0]['formats'][0]['url'], 'title': song_list[0]['title']},
        #             {'source': song_list[1]['formats'][0]['url'], 'title': song_list[1]['title']},
        #             {'source': song_list[2]['formats'][0]['url'], 'title': song_list[2]['title']}]
        # else:
        return [{'source': song_list[0]['formats'][0]['url'], 'title': song_list[0]['title']}]

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing_song = True
            music_url = self.music_queue[0]['source']
            self.current_song = self.music_queue[0]['title']
            self.music_queue.pop(0)
            self.voice_channel.play(discord.FFmpegPCMAudio(music_url, **self.FFMPEG_OPTIONS),
                                    after=lambda e: self.play_next())
        else:
            self.is_playing_song = False
            self.current_song = ""

    async def play_music(self):
        if len(self.music_queue) > 0:
            self.is_playing_song = True
            music_url = self.music_queue[0]['source']
            self.current_song = self.music_queue[0]['title']
            print(f"Fila de musicas: {self.music_queue}")
            self.music_queue.pop(0)
            self.voice_channel.play(discord.FFmpegPCMAudio(music_url, **self.FFMPEG_OPTIONS),
                                    after=lambda e: self.play_next())
        else:
            self.is_playing_song = False
            self.current_song = ""
            await self.voice_channel.disconnect()

    @app_commands.command(name="play", description="Toca uma música do youtube")
    @app_commands.describe(search_parameter="Digite o nome ou a url da música que deseja tocar.")
    async def play(self, interaction: discord.Interaction, search_parameter: str):
        await interaction.response.defer(thinking=True)
        try:
            voice_channel = interaction.user.voice.channel
        except Exception:
            embed = discord.Embed(
                colour=12255232,
                description='Você deve estar conectado a um canal de voz para tocar música.'
            )
            await interaction.followup.send(embed=embed)
            return
        else:
            songs = self.search_youtube_music(search_parameter)
            if isinstance(songs, type(False)):
                embed = discord.Embed(
                    colour=12255232,
                    description='Ocorreu algum problema ao procurar sua música. Mude os parâmetros de busca e tente novamente.'
                )
                await interaction.followup.send(embed=embed)
            else:
                if self.voice_channel is "" and self.is_playing_song is False:
                    self.voice_channel = await voice_channel.connect()
                elif self.voice_channel is not "" and self.is_playing_song is False:
                    await self.voice_channel.disconnect()
                    self.voice_channel = await voice_channel.connect()
                # if len(songs) > 1:
                #     view = DropdownView(songs= songs, music_player= self)
                #     await interaction.followup.send(view=view)
                # else:
                embed = discord.Embed(
                    colour=7419530,
                    description=f"Você adicionou a música **{songs[0]['title']}** à fila!"
                )
                await interaction.followup.send(embed=embed, view=OwnerButton())
                self.music_queue.append(songs[0])
                if self.is_playing_song is False:
                    await self.play_music()

    @app_commands.command(name="pular", description="Pula a atual música que está tocando.")
    @app_commands.default_permissions(manage_channels=True)
    async def pular(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if self.voice_channel is not "" and self.is_playing_song is True:
            self.voice_channel.stop()
            await self.play_music()
            if len(self.music_queue) > 0:
                current_queue = ""
                for i in range(0, len(self.music_queue)):
                    current_queue += f'**{i + 1} - **' + self.music_queue[i][0]['title'] + "\n"
                embed = discord.Embed(
                    colour=7419530,
                    description=f"A música atual foi pulada.\n\nFila atual:{current_queue}"
                )
            elif len(self.music_queue) is 0 and self.is_playing_song is True:
                embed = discord.Embed(
                    colour=7419530,
                    description=f"A música foi pulada. Agora estamos tocando **{self.current_song}**."
                )
            else:
                embed = discord.Embed(
                    colour=7419530,
                    description=f"A música atual foi pulada e não tem nenhuma outra para ser tocada a seguir."
                )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                colour=12255232,
                description=f"Não tem nenhuma música tocando para ser pulada."
            )
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="fila", description="Mostra as atuais músicas da fila.")
    async def fila(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        current_queue = ""
        for i in range(0, len(self.music_queue)):
            current_queue += f'**Fila das músicas a serem tocadas:**\n\n**{i + 1} - **' + self.music_queue[i]['title'] + "\n"

        print(current_queue)
        if current_queue != "":
            embed = discord.Embed(
                colour=7419530,
                description=f"{current_queue}"
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                colour=12255232,
                description='Não existe músicas na fila no momento.'
            )
            await interaction.followup.send(embed=embed)

    @pular.error
    async def skip_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                colour=12255232,
                description=f"Você precisa da permissão **Gerenciar canais** para pular músicas."
            )
            await interaction.followup.send(embed=embed)
        else:
            raise error

async def setup(client):
    await client.add_cog(MusicPlayer(client))
