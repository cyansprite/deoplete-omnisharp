if exists('g:loaded_deoplete_omnisharp')
    finish
endif

let g:loaded_deoplete_omnisharp = 1
if has('unix')
    let g:deoplete_omnisharp_exe_path   = get(g:, "deoplete_omnisharp_exe_path", '~/.local/share/nvim/plugged/deoplete-omnisharp/omnisharp-server/OmniSharp/bin/Debug/OmniSharp.exe')
else
    let g:deoplete_omnisharp_exe_path   = get(g:, "deoplete_omnisharp_exe_path", 'c:/users/bcoffman/.local/share/nvim/plugged/deoplete-omnisharp/omnisharp-server/OmniSharp/bin/Debug/OmniSharp.exe')
endif
let g:deoplete_omnisharp_port   = get(g:, "deoplete_omnisharp_port", 9999)

function! DeopleteOmnisharpReconnectServer()
    if has_key(g:,'deoplete_omnisharp_finished_loading')
        let g:deoplete_omnisharp_finished_loading = 0
        echohl ErrorMsg
        echom "Omnisharp Server disconnected, reconnecting now..."
        echohl NONE
    endif

    if has('unix')
        let commd = g:deoplete_omnisharp_exe_path . ' -p ' .
                    \ string(g:deoplete_omnisharp_port) .
                    \ s:find_solution_file()
    else
        let commd = [g:deoplete_omnisharp_exe_path, '-p', string(g:deoplete_omnisharp_port), s:find_solution_file()]
    endif

    let job = jobstart(commd,
        \ {'on_stdout': 'DeopleteOmnisharpReconnectServerOut',
        \  'on_stderr': 'DeopleteOmnisharpReconnectServerError'}
    \)

    " echo job
endfunction

function! DeopleteOmnisharpReconnectServerOut(job_id, data, event)
    " echom string(a:data)
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

function! s:find_solution_file()
    let dir = expand('%:p:h')
    let lastfolder = ''
    let sln = ''

    while dir !=# lastfolder
        let sln = globpath(dir, '*.sln')
        if sln != ""
            let sln = ' -s ' . sln
            break
        endif
        let lastfolder = dir
        let dir = fnamemodify(dir, ':h')
    endwhile

    return sln
endfunction
