import neovim;
import sys;
import re;
import time;
import string;
import json
import urllib
import urllib.request
import urllib.parse
import os.path

@neovim.plugin
class omnisharp(object):

    def __init__(self, nvim):
        self.nvim = nvim;
        self.init = False;
        self.omniserver = None;

        # user options...
        self.updateInInsert = False;

    # autocmd {{{
    @neovim.autocmd('VimEnter', pattern='*', eval='&filetype', sync=True)
    def on_vim(self, filetype):
        self.alwaysMatchID = self.nvim.new_highlight_source();
        self.unmatchedID   = self.nvim.new_highlight_source();
        self.init = True;
        self.nvim.async_call(lambda:[self.entrance(filetype)]);

    @neovim.autocmd('VimLeave', pattern='*', eval='', sync=True)
    def exit(self):
        self.omniserver.go_the_fuck_away()

    @neovim.autocmd('InsertLeave', pattern='*.cs', eval='b:changedtick', sync=False)
    def on_leave(self,tick):
        if self.omniserver is not None:
            self.omniserver.update(tick);

    # @neovim.autocmd('TextChangedI', pattern='*', eval='b:changedtick', sync=False)
    # def on_change_i(self,tick):
    #     if self.omniserver is not None:
    #         self.omniserver.update(tick);

    @neovim.autocmd('TextChanged', pattern='*.cs', eval='b:changedtick', sync=False)
    def on_change(self,tick):
        if self.omniserver is not None:
            self.omniserver.update(tick);

    @neovim.autocmd('CursorHold', pattern='*.cs', eval='b:changedtick', sync=False)
    def on_hold(self,tick):
        if self.omniserver is not None:
            self.omniserver.update(tick);

    @neovim.autocmd('BufEnter', pattern='*.cs', eval='&filetype', sync=True)
    def on_buf_enter(self,filetype):
        if self.init:
            self.nvim.async_call(lambda:[self.entrance(filetype)]);

    def entrance(self,filetype):
        if self.init:
            if self.omniserver:
                self.omniserver.reset_tick()
            else:
                omni = OmniServer(self.nvim, filetype, self.init, self.alwaysMatchID, self.unmatchedID);
                self.omniserver = omni;
                self.omniserver.update(self.nvim.eval('b:changedtick'))


    # @neovim.autocmd('CursorHoldI', pattern='*', eval='getcurpos()', sync=False)
    # def on_hold_i(self,cur):
    #     if self.currentlighter is not None:
    #         self.currentlighter.current(cur);

    # @neovim.autocmd('CursorMoved', pattern='*', eval='getcurpos()', sync=False)
    # def on_move(self,cur):
    #     if self.currentlighter is not None:
    #         self.currentlighter.current(cur);

    # @neovim.autocmd('CursorMovedI', pattern='*', eval='getcurpos()', sync=False)
    # def on_move_i(self,cur):
    #     if self.currentlighter is not None:
    #         self.currentlighter.current(cur);
    # }}}

    # Commands {{{
    @neovim.command("OmniRename", range='', nargs='1')
    def safe_rename(self, args, range):
        self.omniserver.safe_rename(args[0])

    @neovim.command("OmniUsage", range='', nargs='0')
    def find_usuages(self, args, range):
        self.omniserver.find_usuages();

    @neovim.command("OmniMembers", range='', nargs='0')
    def find_members(self, args, range):
        self.omniserver.find_members();

    @neovim.command("OmniSyntaxErrors", range='', nargs='*')
    def syntax_errors(self, args, range):
        self.omniserver.find_syntax_errors()

    @neovim.command("OmniFixUsings", range='', nargs='*')
    def fix_usings(self, args, range):
        self.omniserver.fix_usings()

    @neovim.command("OmniSemanticErrors", range='', nargs='*')
    def semantic_errors(self, args, range):
        self.omniserver.find_semantic_errors()

    @neovim.command("OmniAllTypes", range='', nargs='*')
    def find_types(self, args, range):
        self.omniserver.find_types()

    @neovim.command("OmniAllSymbols", range='', nargs='*')
    def find_symbols(self, args, range):
        self.omniserver.find_symbols()

    @neovim.command("OmniTypes", range='', nargs='*')
    def find_types(self, args, range):
        self.omniserver.find_types_only_this_file()

    @neovim.command("OmniSymbols", range='', nargs='*')
    def find_symbols(self, args, range):
        self.omniserver.find_symbols_only_this_file()

    @neovim.command("OmniGoToDefintion", range='', nargs='*')
    def go_to_def(self, args, range):
        self.omniserver.go_to_def()

    @neovim.command("OmniFindImplementations", range='', nargs='*')
    def find_impl(self, args, range):
        self.omniserver.find_impl()
    #}}}

class OmniServer():
    def __init__(self,nvim,filetype,init,alwaysMatchID, unmatchedID):
        self.nvim = nvim;
        self.alwaysMatchID = alwaysMatchID;
        self.unmatchedID = unmatchedID;

        self.symbols = [];
        self.types   = [];

        self.gtfo        = False;
        self.go          = False;
        self.scoping     = False;
        self.locked      = False;
        self.lastUpdate  = 0;
        self.lasttick    = 0;
        self.currentTick = -1;
        self.updateInterval = .15;
        self.lastfile    = "";
        self.filetype    = filetype;
        self.buffer      = self.nvim.current.buffer;
        self.window      = self.nvim.current.window;
        # True Boundary : (?<=\s)m(?=\s)|^m(?=\s)|(?<=\s)m$|^m$

        if init and self.am_i_allowed():
            self.handle_unmatched();

    def go_the_fuck_away(self):
        self.gtfo = True;

    def reset_tick(self):
        self.currentTick = -1;
        self.lasttick = 0;
        self.buffer = self.nvim.current.buffer;
        self.window = self.nvim.current.window;

    def change(self,tick):
        self.lasttick = tick;
        self.lastUpdate = time.time();
        self.buffer.clear_highlight(self.unmatchedID, 0, -1);
        self.talk("updateBuffer")

    def update(self,tick):
        if not self.locked:
            self.locked = True;
            self.single_loop();
        else:
            self.change(tick);

    def single_loop(self):
        while not self.gtfo:
            self.nvim.out_write('');
            if not self.am_i_allowed():
                continue;
            if (time.time() - self.lastUpdate) > self.updateInterval and self.currentTick < self.lasttick:
                self.talk("updateBuffer")
                self.currentTick = self.lasttick;
                self.buffer.clear_highlight(self.unmatchedID, 0, -1);
                self.handle_unmatched();

    def handle_unmatched(self):
        self.lastUpdate = time.time();
        self.get_unmatched()

    def get_unmatched(self):
        def fill_up(quickfix):
            text = quickfix['Text'].partition("\t")[0]
            line = quickfix['Line']
            column = self.buffer[line - 1].find(text,quickfix['Column'])
            return (line - 1, column, column + len(text))

        l  = self.talk("findsymbols")
        l2 = self.talk("findtypes")
        if l is None or l2 is None:
            return;

        syms = []
        typs = []
        for quickfix in l["QuickFixes"]:
            if quickfix['FileName'] == self.buffer.name:
                syms.append(fill_up(quickfix));
        for quickfix in l2["QuickFixes"]:
            if quickfix['FileName'] == self.buffer.name:
                typs.append(fill_up(quickfix));

        for item in syms:
            self.buffer.add_highlight("Function" , item[0], item[1], item[2], self.unmatchedID);
        for item in typs:
            self.buffer.add_highlight("Boolean" , item[0], item[1], item[2], self.unmatchedID);

        self.symbols = syms;
        self.types = typs;

    # Omnisharps {{{
    def am_i_allowed(self):
        if self.go:
            return True
        try:
            if self.nvim.eval("g:deoplete_omnisharp_finished_loading"):
                self.go = True
                return True
        except :
            return False
        return False

    def safe_rename(self, rename):
        parameters = {}
        parameters['renameto'] = rename;
        l = self.talk('/rename', parameters);
        if l is None: 
            return;
        self.nvim.out_write("{}\n".format(l))

    def fix_usings(self):
        l = self.talk('fixusings')
        if l is None:
            return;
        lines = [str(i) for i in self.buffer[:]]
        appendages = [];
        skipdex = 0;
        curdex = 0;
        for line in l['Buffer'].split("\n"):
            if lines[curdex - skipdex] != line:
                appendages.append((curdex - skipdex,line));
                skipdex += 1;
            curdex += 1;

        for append in appendages:
            self.buffer.append(append[1],append[0])

        self.qf(l, 'AmbiguousResults')

    def find_usuages(self):
        l = self.talk('/findusages')
        if l is not None:
            self.qf(l, "QuickFixes");

    def find_members(self):
        l = self.talk('/currentfilemembersasflat')
        if l is not None:
            self.qf(l);

    def go_to_def(self):
        l = self.talk("gotodefinition")
        if l is not None and l['FileName'] is not None:
            self.nvim.out_write("{}\n".format(l))
            self.nvim.command("e +{} {}|norm! {}|".format(l['Line'], l['FileName'], l['Column']))
        else:
            self.nvim.out_write("No definition found\n")

    def find_impl(self):
        l = self.talk("findimplementations")
        if l is not None:
            self.nvim.out_write("{}\n".format(l))
            self.qf(l, "QuickFixes")

    def qf(self, l, key=None, local=False):
        items = []
        if key is not None:
            l = l[key];

        for quickfix in l:
            if key == "Errors":
                text = quickfix['Message'].partition("\t")[0]
            else:
                text = quickfix['Text'].partition("\t")[0]

            if local and quickfix['FileName'] != self.buffer.name:
                continue;
            item = {
                'filename': os.path.relpath(quickfix['FileName']),
                'text': text,
                'lnum': quickfix['Line'],
                'col': quickfix['Column'],
                'vcol': 0
            }
            items.append(item)

        self.nvim.command("call setqflist({})".format(items))
        self.nvim.command("copen")

    def find_syntax_errors(self):
        l = self.talk("syntaxerrors")
        if l is not None and l['Errors']:
            self.nvim.out_write("{}\n".format(l))
            self.qf(l, "Errors")
        else:
            self.nvim.out_write("No syntax errors\n")

    def find_semantic_errors(self):
        l = self.talk("semanticerrors")
        if l is not None and l['Errors']:
            self.nvim.out_write("{}\n".format(l))
            self.qf(l, "Errors")
        else:
            self.nvim.out_write("No semantic errors\n")

    def find_symbols(self):
        l = self.talk("findsymbols")
        if l is not None:
            self.qf(l, "QuickFixes")

    def find_types(self):
        l = self.talk("findtypes")
        if l is not None:
            self.qf(l, "QuickFixes")

    def find_symbols_only_this_file(self):
        l = self.talk("findsymbols")
        if l is not None:
            self.qf(l, "QuickFixes", True)

    def find_types_only_this_file(self):
        l = self.talk("findtypes")
        if l is not None:
            self.qf(l, "QuickFixes", True)

    def talk(self, command, addParams = {}):
        if not self.am_i_allowed():
            return None

        url = "http://localhost:{}/{}".format(self.nvim.eval('g:deoplete_omnisharp_port'), command)
        params = {
            'line': str(self.window.cursor[0]),
            'column': str(self.window.cursor[1]+1),
            'buffer': '\n'.join(self.buffer),
            'filename': str(self.buffer.name),
        }
        if params:
            params.update(addParams)

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
            self.nvim.command("call DeopleteOmnisharpReconnectServer()")
            e = sys.exc_info()[0]
            self.nvim.out_write("{}\n".format(e))
            return None

        if r is None or len(r) == 0:
            return None

        l = json.loads(r)
        if l is None:
            return None
        return l

    # }}}
