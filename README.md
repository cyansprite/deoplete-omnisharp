# deoplete-omnisharp

##### Currently only for linux, will test windows later.
##### Confirmed work bash on ubuntu on windows

### Demo 2 - Currently reverted until I have a solid plan and time to fix.
<a href="https://imgur.com/843U34s"><img src="https://i.imgur.com/843U34s.gif" title="source: imgur.com" /></a>
### Demo
<a href="https://imgur.com/FNcLDAu"><img src="https://i.imgur.com/FNcLDAu.gif" title="source: imgur.com" /></a>

### Features
- Async autocompletion via deoplete and omnisharp server
- Auto start server
- If it hasn't started yet don't freak out, just return [] ( i.e. regular completions )
- If it has started and disconnected then fix it automatically on next attempt of completion.

### Dependencies
- [deoplete](https://github.com/Shougo/deoplete.nvim)
- [mono](http://www.mono-project.com/) (I'm on 5.2.0)

### Install
- With Plug
  ```vim
  Plug 'cyansprite/deoplete-omnisharp' , {'do': './install.sh'}
  ```
- Without Plug download it or use your package manager
  ```
  cd ~/.local/share/nvim/plugged/deoplete-omnisharp
  ./install.sh
  ```
  
### Options
```vim
let g:deoplete_omnisharp_exe_path   = get(g:, "deoplete_omnisharp_exe_path", '~/.local/share/nvim/plugged/deoplete-omnisharp/omnisharp-server/OmniSharp/bin/Debug/OmniSharp.exe')
let g:deoplete_omnisharp_port   = get(g:, "deoplete_omnisharp_port", 9999)
```
