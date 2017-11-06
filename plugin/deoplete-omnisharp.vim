if exists('g:loaded_deoplete_omnisharp')
    finish
endif

let g:loaded_deoplete_omnisharp = 1
let g:deoplete_omnisharp_exe_path   = get(g:, "deoplete_omnisharp_exe_path", '~/.local/share/nvim/plugged/deoplete-omnisharp/omnisharp-server/OmniSharp/bin/Debug/OmniSharp.exe')
let g:deoplete_omnisharp_port   = get(g:, "deoplete_omnisharp_port", 9999)

function! DeopleteOmnisharpReconnectServer()
    if has_key(g:,'deoplete_omnisharp_finished_loading')
        let g:deoplete_omnisharp_finished_loading = 0
        echohl ErrorMsg
        echom "Omnisharp Server disconnected, reconnecting now..."
        echohl NONE
    endif

    let commd = 'mono '.
                \ g:deoplete_omnisharp_exe_path . ' -p '.
                \ string(g:deoplete_omnisharp_port)

    call jobstart(commd,
        \ {'on_stdout': 'DeopleteOmnisharpReconnectServerOut',
        \  'on_stderr': 'DeopleteOmnisharpReconnectServerError'}
    \)
endfunction

function! DeopleteOmnisharpReconnectServerOut(job_id, data, event)
    if match(a:data, "Solution has finished loading") != -1
        let g:deoplete_omnisharp_finished_loading = 1
        echohl DiffAdd
        echom "OmniSharp server initialized, you can now get semantic completions."
        echohl NONE
    endif
endfunction

function! DeopleteOmnisharpReconnectServerError(job_id, data, event)
    echom printf('%s: %s',a:event,string(a:data))
endfunction
