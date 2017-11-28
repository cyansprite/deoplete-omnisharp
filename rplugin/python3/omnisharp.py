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

    @neovim.autocmd('CursorMoved', pattern='*.cs', sync=False)
    def on_move(self):
        if self.omniserver is not None:
            self.omniserver.type_lookup();

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

    @neovim.command("OmniFixUsings", range='', nargs='*')
    def fix_usings(self, args, range):
        self.omniserver.fix_usings()

    @neovim.command("OmniCodeCheck", range='', nargs='*')
    def check_code(self, args, range):
        self.omniserver.code_check()

    @neovim.command("OmniFixCode", range='', nargs='*')
    def fix_code(self, args, range):
        self.nvim.out_write("{}\n".format(range))
        self.omniserver.fix_code(range);

    @neovim.command("OmniLookup", range='', nargs='*')
    def lookup_types(self, args, range):
        self.omniserver.type_lookup();

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
        self.alltypes = [];

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
            typs.append(fill_up(quickfix));
        for item in syms:
            l = self.talk("findsymbols")
            if l is None:
                continue;

        for item in syms:
            self.buffer.add_highlight("Member" , item[0], item[1], item[2], self.unmatchedID);
        for item in typs:
            self.buffer.add_highlight("Float" , item[0], item[1], item[2], self.unmatchedID);

        self.symbols = syms;
        self.types = typs;

        l3 = self.talk("lookupalltypes")
        if l3 is not None and l3['Types']:
            self.alltypes = l3['Types'].split();
            self.nvim.command("syn keyword csAllTypes {}".format(l3['Types']))
            self.nvim.command("hi link csAllTypes Label")

    # Omnisharps {{{
    def type_lookup(self):
        l = self.talk('/typelookup');
        if l is not None and l['Type']:
            commandstring = "";
            reg = re.compile(r'[;|)|(|.|\s]')
            it = reg.finditer(l['Type']);
            l = l['Type']
            lastpos = 0;
            lasttype = "";
            for x in it:
                self.nvim.out_write("{}\n".format(x.group()));
                # type or label
                if x.group() == " ":
                    if lasttype != 'Type':
                        commandstring += "echohl {} | echon '{}' | ".format("Type", l[lastpos:x.start()]);
                        lasttype = 'Type';
                    else:
                        commandstring += "echohl {} | echon '{}' | ".format("Identifier", l[lastpos:x.start()]);
                        lasttype = 'Identifier';
                # Class
                elif x.group() == ".":
                    commandstring += "echohl {} | echon '{}' | ".format("Float", l[lastpos:x.start()]);
                # Function
                elif x.group() == "(":
                    commandstring += "echohl {} | echon '{}' | ".format("Function", l[lastpos:x.start()]);
                # Member
                elif x.group() == ";":
                    commandstring += "echohl {} | echon '{}' | ".format("Member", l[lastpos:x.start()]);
                # Param
                elif x.group() == ")" or x.group() == ",":
                    commandstring += "echohl {} | echon '{}' | ".format("Identifier", l[lastpos:x.start()]);
                lastpos = x.start() + 1;
                commandstring += "echohl {} | echon '{}' | ".format("Operator", l[x.start():x.end()]);

            # if we don't have any punct, like just on a type,
            # or if we don't have any ending punc like with System.Single
            if commandstring == "" or lastpos < len(l):
                l = l[lastpos:len(l)]
                if l in self.alltypes:
                    commandstring += "echohl {} | echon '{}' | ".format("Label", l);
                else:
                    commandstring += "echohl {} | echon '{}' | ".format("Type", l);
            self.nvim.out_write("{} : {}\n".format(lastpos, len(l)))


            commandstring += " echohl NONE"
            self.nvim.command(commandstring);

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
        l = self.talk('updatebuffer')
        l = self.talk('fixusings')
        if l is None:
            return;

        self.nvim.out_write("{}\n".format(l))
        self.change_buffer(l, "Buffer")
        if l['AmbiguousResults']:
            self.qf(l, 'AmbiguousResults')

    def change_buffer(self, l, key):
        diff = False;
        dex = 0;
        for line in l[key].split("\n"):
            if self.buffer[dex] != line:
                diff = True;
                break;
            dex += 1;
        if diff:
            self.buffer[:] = l[key].split("\n")

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
            column = -1;
            line = quickfix['Line']
            if key == "Errors":
                text = quickfix['Message'].partition("\t")[0]
            else:
                text = quickfix['Text'].partition("\t")[0]
                column = self.buffer[line - 1].find(text,quickfix['Column'])

            if column == -1:
                column = quickfix['Column'] - 1;

            if local and quickfix['FileName'] != self.buffer.name:
                continue;
            item = {
                'filename': os.path.relpath(quickfix['FileName']),
                'text': text,
                'lnum': line,
                'col': column + 1,
                'vcol': 0
            }
            items.append(item)

        self.nvim.command("call setqflist({})".format(items))
        self.nvim.command("copen")
    # def getCodeIssues():
    #     js = getResponse('/getcodeissues')
    #     return get_quickfix_list(js, 'QuickFixes')

    # def codeCheck():
    #     js = getResponse('/codecheck')
    #     return get_quickfix_list(js, 'QuickFixes')

    def fix_code(self, ran = None):
        l = self.talk("fixcodeissue");
        if l is not None:
            self.change_buffer(l, "Text")
        else:
            self.nvim.out_write("No fixes\n")

    def lookup_types(self):
        l = self.talk("lookupalltypes")
        if l is not None:
            self.nvim.out_write("{}\n".format(l))
            # self.qf(l, "QuickFixes")
        else:
            self.nvim.out_write("No fixes\n")

    def code_check(self):
        l = self.talk("codecheck")
        if l is not None and l['QuickFixes']:
            self.qf(l, "QuickFixes")
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
