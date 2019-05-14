import re
import json
import urllib
import urllib.request
import urllib.parse
from .base import Base

class Source(Base):
    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = 'cs'
        self.go = False
        self.mark = '[CS]'
        self.rank = 1000
        self.filetypes = ['cs']
        self.input_pattern = '\.\w*'
        self.is_bytepos = True

    def get_complete_position(self, context):
        m = re.search(r'\w*$', context['input'])
        return m.start() if m else -1

    # Can we get completions ( i.e. is the server alive )
    def am_i_allowed(self):
        if self.go:
            return True
        try:
            if self.vim.eval("g:deoplete_omnisharp_finished_loading"):
                self.go = True
                return True
        except :
            return False
        return False

    def gather_candidates(self, context):
        if not self.am_i_allowed():
            return []

        url = "http://localhost:{0}/autocomplete".format(self.vim.eval('g:deoplete_omnisharp_port'))
        win = self.vim.current.window
        lines = [str(i) for i in self.vim.current.buffer[:]]

        params = {
            'line': str(win.cursor[0]),
            'column': str(win.cursor[1]+1),
            'buffer': '\n'.join(lines),
            'filename': str(self.vim.current.buffer.name),
            'wordToComplete': context['complete_str'],
            'WantMethodHeader': True,
            'ForceSemanticCompletion': True,
            'WantImportableTypes': True,
            'WantReturnType': True,
            'WantDocumentationForEveryCompletionResult': True
        }
        data = bytes(json.dumps(params), 'utf-8')

        req = urllib.request.Request(
            url,
            data,
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req) as f:
                r = str(f.read(), 'utf-8')
        except:
            self.vim.command("call DeopleteOmnisharpReconnectServer()")
            return []

        if r is None or len(r) == 0:
            return []

        l = json.loads(r)
        if l is None:
            return []

        completions = []
        for item in l:
            # description = item['Description'].replace('\r\n', '\n') if item['Description'] is not None else ''

            completions.append(dict(
                word=item['CompletionText'],
                abbr=item['CompletionText'],
                info=item['Description'],
                menu=item['MethodHeader'] or '',
                kind=item['ReturnType'] or item['DisplayText'],
                icase=1,
                dup=1))

        return completions
