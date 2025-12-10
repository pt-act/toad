# Toad

Welcome to the Toad repository!

This repository is currently private.
If you are here, it is because you had a personal invite from me, and I value your opinion.
I'm looking for early feedback, and potential collaboration in the future (if you're interested).

I am particularly interested in your feedback on usability right now.
This class of apps is so new, I think there is plenty of room for innovation.

Please use the Discussions tab for your feedback and bug reports.
Avoid issues and PRs for now, unless we've agreed on them in the Discussions tab.

Toad is very much a work in progress.
See [notes.md](https://github.com/Textualize/toad/blob/main/notes.md) for details about what to expect.

<table>

  <tbody>

  <tr>
    <td><img width="1338" height="1004" alt="Screenshot 2025-10-23 at 08 58 58" src="https://github.com/user-attachments/assets/98387559-2e10-485a-8a7d-82cb00ed7622" /></td> 
    <td><img width="1338" height="1004" alt="Screenshot 2025-10-23 at 08 59 04" src="https://github.com/user-attachments/assets/d4231320-b678-47ba-99ce-02746ca2622b" /></td>    
  </tr>

  <tr>
    <td><img width="1338" height="1004" alt="Screenshot 2025-10-23 at 08 59 22" src="https://github.com/user-attachments/assets/ddba550d-ff33-45ad-9f93-281187f5c974" /></td>
    <td><img width="1338" height="1004" alt="Screenshot 2025-10-23 at 08 59 37" src="https://github.com/user-attachments/assets/e7943272-39a5-40a1-bedf-e440002e1290" /></td>
  </tr>
    
  </tbody>

  
</table>



## What is Toad?

Toad is a universal interface to AI agents, which includes chat bots and agentic coding.
Here's a tongue-in-check write up on my blog: https://willmcgugan.github.io/announcing-toad/

## Talk about Toad!

Please **do** talk about Toad!
Generating a buzz ahead of the first open release will be very beneficial.

You may share your thoughts on social media in addition to screenshots and videos (but obviously no code from this repository).
Please [tag me](https://github.com/willmcgugan) in your posts.

I intend to release a first public version when there is enough core functionality.
Progress has been good. So I would expect a release in December.

## Requirements

Works on Linux and Mac. Windows works with WSL.

Any terminal will work, although if you are using the default terminal on macOS you will get a much reduced experience.
I recommend [Ghostty](https://ghostty.org/) which is fully featured and has amazing performance.

## Getting started

Assuming you have [UV](https://docs.astral.sh/uv/getting-started/installation/) installed, running `toad` should be as simple as cloning the repository and running the following:

```
uv run toad
```

If your favorite agent isn't listed, you can use the `acp` subcommand:

```
uv run toad acp "gemini --experimental-acp"
```

## Web terminal

There is an experimental web server mode. Add `--serve` to the CLI command and click the URL in the terminal.

## Installing agents

Agents need to be installed separately, and require support for [ACP](https://agentclientprotocol.com/overview/introduction).

You will need to install the agent and authenticate at least once with the agent's own CLI tool.
After that you can use Toad to interact with it.


## Thanks

Thanks for being a part of this!

See you in discussions.

I'm also in the #toad channel on the [Textualize discord server](https://discord.gg/Enf6Z3qhVr).






