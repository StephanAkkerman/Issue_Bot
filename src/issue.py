##> Imports
# > 3rd party dependencies
from github import Github
import emoji
import yaml

# > Discord dependencies
import discord
from discord.ext import commands

with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.full_load(f)

# Get the access token
gh_token = config["ISSUE"]["TOKEN"]

# Initialize GH client and repo
g = Github(gh_token)
repo = g.get_repo(config["ISSUE"]["REPO"])
labels = repo.get_labels()

# Get the emojis and lists of them
label_emojis = [x.name.split()[-1] for x in labels]
label_text = [" ".join(x.name.split()[:-1]) for x in labels]
label_names = [x.name for x in labels]

# Convert label_emojis to discord emojis
disc_emojis = [emoji.emojize(gh_emoji, use_aliases=True) for gh_emoji in label_emojis]

# Discord emoji names -> gh emoji names
emoji_dict = dict(zip([emoji.demojize(x) for x in disc_emojis], label_emojis))

# Label_emojis -> label_names
label_dict = dict(zip(label_emojis, label_names))


class Issue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=[config['ISSUE']['ALIAS']])
    async def issue(self, ctx, *input):
        """Create a new issue on GitHub

        Usage: `!issue <title>`
        Use this command to create a new issue on GitHub.
        """

        # Just like the !announcement
        if len(input) == 0:
            raise commands.UserInputError()

        title = " ".join(input)

        # Confirm command used
        create_issue = await ctx.send(
            f"Creating issue with title **{title}**. What should the description be?"
        )

        # Await announcement body
        msg = await self.bot.wait_for(
            "message",
            check=lambda message: message.author == ctx.author
            and message.channel == ctx.channel,
        )

        # Create Discord embed from msg
        e = discord.Embed(
            title=title,
            description=msg.content,
            color=0x00FFFF,
        )

        # Comine disc emoji + label name
        field_labels = [m + " " + n for m, n in zip(disc_emojis, label_text)]

        field_text = "\n".join(field_labels)

        # Set embed properties
        e.add_field(name="Labels", value=field_text, inline=False)
        e.set_thumbnail(
            url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
        )
        e.set_footer(text="This is a preview. Please confirm that all info is correct.")

        # Send preview announcement
        preview_msg = await ctx.send(embed=e)
        await preview_msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await preview_msg.add_reaction("\N{CROSS MARK}")

        # Add label emojis
        for disc_emoji in disc_emojis:
            await preview_msg.add_reaction(disc_emoji)

        # Handle preview accept/deny using reactions
        reaction = await self.bot.wait_for(
            "reaction_add",
            check=lambda r, u: (
                str(r.emoji) == "\N{WHITE HEAVY CHECK MARK}"
                or str(r.emoji) == "\N{CROSS MARK}"
            )
            and u == ctx.author,
        )

        # Get all the reactions
        reactions = discord.utils.get(
            self.bot.cached_messages, id=preview_msg.id
        ).reactions
        reacted_labels = [
            x.emoji
            for x in reactions
            if x.count > 1
            and str(x.emoji) != "\N{CROSS MARK}"
            and str(x.emoji) != "\N{WHITE HEAVY CHECK MARK}"
        ]

        # Delete clutter
        await ctx.message.delete()
        await create_issue.delete()
        await msg.delete()
        await preview_msg.delete()

        # If check marked is clicked create the issue
        if reaction[0].emoji == "\N{WHITE HEAVY CHECK MARK}":
            make_issue(title, msg.content, reacted_labels, ctx.author)
            await ctx.send(f"Issue succesfully created! \n{get_issue_url()}")

        elif reaction[0].emoji == "\N{CROSS MARK}":
            await ctx.send(
                f"Make a new issue using `!issue <title>` and follow the instructions."
            )


def get_issue_url():
    """Returns the url of the new issue"""

    new_issue = repo.get_issues(state="open")[0]

    return f"https://github.com/{config['ISSUE']['REPO']}/issues/{new_issue.number}"


def make_issue(t, b, l, author):

    b += f"\nRequested by {author}"

    real_labels = []

    # Get text of emoji
    if l != []:
        demoji = [emoji.demojize(emo) for emo in l]

        # Lookup in dict
        for d in demoji:
            label = label_dict[emoji_dict[d]]
            real_labels += [label]

    # Create the issue
    repo.create_issue(title=t, body=b, labels=real_labels)


def setup(bot):
    bot.add_cog(Issue(bot))
