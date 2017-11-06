if exists('g:loaded_ftdeoplete_omnisharp_loaded')
    finish
endif

let g:loaded_ftdeoplete_omnisharp_loaded = 1
let commd = 'mono '.
            \ '~/.local/share/nvim/plugged/deoplete-omnisharp/omnisharp-server/OmniSharp/bin/Debug/OmniSharp.exe -p '.
            \ string(g:deoplete_omnisharp_port)

call DeopleteOmnisharpReconnectServer()

" call jobstart(commd,
"     \ {'on_stdout': 'Out',
"     \  'on_stderr': 'Error'}
" \)

" function! Out(job_id, data, event)
"     if match(a:data, "Solution has finished loading") != -1
"         let g:deoplete_omnisharp_finished_loading = 1
"         echohl DiffAdd
"         echom "OmniSharp server initialized, you can now get semantic completions."
"         echohl NONE
"     endif
" endfunction
" function! Error(job_id, data, event)
"     echom printf('%s: %s',a:event,string(a:data))
" endfunction
