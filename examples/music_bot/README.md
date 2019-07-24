# Music Bot example
A small bot demonstrating the usage of the andesite.py library.
The bot uses the `andesite.Client` for a single Andesite node.


## Dependencies
- [discord.py](https://github.com/Rapptz/discord.py)
- [colorlog](https://github.com/borntyping/python-colorlog) (OPTIONAL)

## Running the bot
```bash
python music_bot <discord bot token> [options]
```

### Arguments
| Name                | Required | Description                                                           |
|---------------------|:--------:|-----------------------------------------------------------------------|
| --andesite-http     |     ✔    | HTTP endpoint for the Andesite node                                   |
| --andesite-ws       |     ✔    | WebSocket endpoint for the Andesite node                              |
| --andesite-password |     🗙    | Password for the Andesite node. If not specified, no password it used |
| --command-prefix    |     🗙    | Command prefix for the command framework. Defaults to "a."            |


## Information
Most of the files are basically boilerplate code. The interesting part
(i.e. the andesite.py interface) is found in the
`andesite_cog.py` file.