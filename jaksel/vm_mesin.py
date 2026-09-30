# ---------------------------------------------------------------------------
# VM: mesin virtual stack-based untuk bytecode JakselScript
# ---------------------------------------------------------------------------

import threading as _threading

from .vm import (
    CodeUnit, Frame, FungsiVM, _MethodTerikat, _MetodeStatik, _Properti,
    _JakselBase, _EnumBase, _EnumMember, _Modul, _ErrorJaksel,
    _TIDAK_ADA, _METHODS, _tipe_method, _buat_repr,
    JakselError, _Exit, JakselPyModul, JakselPyCallable,
    JakselPyObj, JakselTugas, BuiltinFunction,
    format_value, is_truthy, mirip,
    _tname, _binop, _neg, _cocok_tipe, _cocok_enum, _py_ke_jaksel,
)


class VM:
    """Menjalankan CodeUnit. Satu VM = satu thread eksekusi."""

    def __init__(self, aman=False, file_dir=".", prog_args=None):
        self.aman = aman
        self.file_dir = file_dir
        self.prog_args = list(prog_args or [])
        self.frames = []
        self.handlers = []          # [{"frame":Frame,"target":pc}]
        self._hasil_akhir = None
        self._cache_default = {}    # id(node) -> CodeUnit
        self._modul_cache = {}      # path_abs -> namespace dict
        self._class_ns_stack = []   # stack dict namespace kelas
        self._ns_builtin = {}
        self._nama_builtin = set()
        self._interp_pinjam = None
        self._register_builtins()

    # -- builtins --

    def _register_builtins(self):
        """Pinjam builtin sederhana dari Interpreter; tulis ulang yang
        butuh fungsi Jaksel (luncurkan/saring/petakan/kumpulkan/urut_dengan).
        """
        from .interpreter import Interpreter
        pinjam = Interpreter(aman=self.aman)
        pinjam._file_dir = self.file_dir
        pinjam._argv = self.prog_args
        self._interp_pinjam = pinjam
        lewati = {"luncurkan", "saring", "petakan", "kumpulkan",
                  "urut_dengan"}
        for nama, val in pinjam.globals.vars.items():
            if nama in lewati:
                continue
            self._ns_builtin[nama] = val
        # -- override: butuh memanggil FungsiVM --
        vm = self

        def b_luncurkan(*args):
            if not args:
                raise JakselError("luncurkan() butuh fungsi/talent, bestie.")
            f = args[0]
            daftar = args[1] if len(args) > 1 else []
            if not isinstance(f, (FungsiVM, _MethodTerikat, BuiltinFunction,
                                  JakselPyCallable)):
                raise JakselError("luncurkan() butuh fungsi/talent, bestie.")
            if not isinstance(daftar, list):
                raise JakselError(
                    "argumen kedua luncurkan() harus daftar, bestie.")
            tugas = JakselTugas(getattr(f, "name", "tugas"))

            def _jalan():
                try:
                    if isinstance(f, FungsiVM):
                        tugas._hasil = f.panggil_luar(*daftar)
                    elif isinstance(f, _MethodTerikat):
                        tugas._hasil = f.fungsi.panggil_luar(f.obj, *daftar)
                    else:
                        tugas._hasil = vm._panggil_nilai_sync(
                            f, list(daftar), {}, None)
                except Exception as e:  # noqa: BLE001 - ke tunggu()
                    tugas._error = e
                finally:
                    tugas._event.set()

            th = _threading.Thread(target=_jalan, daemon=True,
                                   name="jaksel-%s" % tugas.name)
            tugas._thread = th
            th.start()
            return tugas

        def _panggil_vm(f, args):
            if isinstance(f, FungsiVM):
                return f.panggil_luar(*args)
            if isinstance(f, _MethodTerikat):
                return f.fungsi.panggil_luar(f.obj, *args)
            return vm._panggil_nilai_sync(f, list(args), {}, None)

        def b_saring(*args):
            if len(args) != 2:
                raise JakselError(
                    "saring() butuh 2 argumen: daftar dan fungsi, bestie.")
            daftar, f = args
            if not isinstance(daftar, (list, str)):
                raise JakselError("saring() butuh daftar/teks, bestie.")
            return [x for x in daftar if is_truthy(_panggil_vm(f, [x]))]

        def b_petakan(*args):
            if len(args) != 2:
                raise JakselError(
                    "petakan() butuh 2 argumen: daftar dan fungsi, bestie.")
            daftar, f = args
            if not isinstance(daftar, (list, str)):
                raise JakselError("petakan() butuh daftar/teks, bestie.")
            return [_panggil_vm(f, [x]) for x in daftar]

        def b_kumpulkan(*args):
            if len(args) != 3:
                raise JakselError("kumpulkan() butuh 3 argumen, bestie.")
            daftar, f, awal = args
            if not isinstance(daftar, (list, str)):
                raise JakselError("kumpulkan() butuh daftar/teks, bestie.")
            acc = awal
            for x in daftar:
                acc = _panggil_vm(f, [acc, x])
            return acc

        def b_urut_dengan(*args):
            if len(args) != 2:
                raise JakselError("urut_dengan() butuh 2 argumen, bestie.")
            daftar, f = args
            if not isinstance(daftar, list):
                raise JakselError("urut_dengan() butuh daftar, bestie.")
            import functools

            def _cmp(a, b):
                return int(_panggil_vm(f, [a, b]))

            return sorted(daftar, key=functools.cmp_to_key(_cmp))

        for nama, fn in [("luncurkan", b_luncurkan), ("saring", b_saring),
                         ("petakan", b_petakan), ("kumpulkan", b_kumpulkan),
                         ("urut_dengan", b_urut_dengan)]:
            self._ns_builtin[nama] = BuiltinFunction(nama, fn)
        # kelas Error bawaan
        self._ns_builtin["Error"] = _ErrorJaksel
        self._nama_builtin = set(self._ns_builtin)

    def _install_builtins_ke(self, frame):
        for k, v in self._ns_builtin.items():
            frame.vars[k] = v

    # -- menjalankan --

    def jalankan(self, unit):
        """Jalankan CodeUnit program utama. Kembalikan nilai akhir."""
        frame = Frame(unit, {}, None, None, "<utama>")
        self._install_builtins_ke(frame)
        self.frames.append(frame)
        try:
            return self._run()
        except JakselError as e:
            if e.trace is None:
                e.trace = self._jejak()
            raise

    def jalankan_modul(self, unit):
        """Jalankan unit sebagai modul; kembalikan dict namespace."""
        frame = Frame(unit, {}, None, None, unit.nama)
        self._install_builtins_ke(frame)
        self.frames.append(frame)
        try:
            self._run()
        except JakselError as e:
            if e.trace is None:
                e.trace = self._jejak()
            raise
        return dict(frame.vars)

    def _jejak(self):
        """Bangun jejak tumpukan dari frames VM: [(nama, baris)]."""
        jejak = []
        # frames[0] = <utama>; frames[i] dipanggil oleh frames[i-1].
        # Baris call-site diambil dari pc si pemanggil.
        for i in range(1, len(self.frames)):
            fr = self.frames[i]
            pemanggil = self.frames[i - 1]
            nama = fr.nama
            if nama.startswith("<") and nama.endswith(">"):
                continue
            baris = None
            if 0 <= pemanggil.pc < len(pemanggil.unit.lines):
                baris = pemanggil.unit.lines[pemanggil.pc]
            jejak.append((nama, baris))
        return jejak

    def _run(self):
        while self.frames:
            frame = self.frames[-1]
            code = frame.unit.code
            if frame.pc >= len(code):
                # habis tanpa RETURN: kembalikan None
                self._selesai_frame(frame, None)
                continue
            op, arg = code[frame.pc]
            frame.pc += 1
            line = frame.unit.lines[frame.pc - 1]
            try:
                self._eksekusi(frame, op, arg, line)
            except _Exit:
                raise
            except JakselError as e:
                if e.line is None:
                    e.line = line
                if not self._tangani_error(e):
                    raise
        return self._hasil_akhir

    def _selesai_frame(self, frame, retval):
        """Pop frame; teruskan retval ke pemanggil (atau jadi hasil akhir)."""
        assert self.frames and self.frames[-1] is frame
        self.frames.pop()
        # buang handler milik frame ini
        self.handlers = [h for h in self.handlers
                         if h["frame"] is not frame]
        if frame.nilai_kembali_paksa is not _TIDAK_ADA:
            retval = frame.nilai_kembali_paksa
        if self.frames:
            self.frames[-1].stack.append(retval)
        else:
            self._hasil_akhir = retval

    def _tangani_error(self, exc):
        """Lempar ke handler yolo terdalam yang masih hidup. True=tertangani."""
        while self.handlers:
            h = self.handlers[-1]
            if h["frame"] not in self.frames:
                self.handlers.pop()
                continue
            self.handlers.pop()
            while self.frames and self.frames[-1] is not h["frame"]:
                self.frames.pop()
            tgt = self.frames[-1]
            tgt.stack.append(exc)
            tgt.pc = h["target"]
            return True
        return False

    # -- variabel --

    def _semua_nama(self, frame):
        s = set()
        f = frame
        while f is not None:
            s.update(f.vars.keys())
            f = f.parent
        return s

    def _load_var(self, frame, nama, line):
        f = frame
        while f is not None:
            if nama in f.vars:
                return f.vars[nama]
            f = f.parent
        msg = ("variabel '%s' belum dikenalin, bestie. "
               "Deklarasi dulu pakai 'bestie %s = ...'") % (nama, nama)
        s = mirip(nama, self._semua_nama(frame))
        if s:
            msg += " Maksudnya '%s'?" % s
        raise JakselError(msg, line)

    def _store_var(self, frame, nama, nilai, line):
        f = frame
        while f is not None:
            if nama in f.vars:
                f.vars[nama] = nilai
                return
            f = f.parent
        msg = "variabel '%s' belum dikenalin, bestie." % nama
        s = mirip(nama, self._semua_nama(frame))
        if s:
            msg += " Maksudnya '%s'?" % s
        raise JakselError(msg, line)

    # -- pemanggilan --

    def _ikat_argumen(self, unit, args, kwargs, line, closure_frame):
        params = unit.params
        variadic = unit.variadic
        bound = {}
        n_pos = len(args)
        for i, (pnama, _d) in enumerate(params):
            if i < n_pos:
                bound[pnama] = args[i]
        if n_pos > len(params) and not variadic:
            raise JakselError(
                "kebanyakan argumen buat '%s', bestie." % unit.nama, line)
        param_names = [p[0] for p in params]
        for k, v in kwargs.items():
            if k not in param_names:
                raise JakselError(
                    "'%s' nggak punya parameter '%s', bestie."
                    % (unit.nama, k), line)
            if param_names.index(k) < n_pos:
                raise JakselError(
                    "argumen '%s' dikasih dua kali, bestie." % k, line)
            bound[k] = v
        for (pnama, pdefault) in params:
            if pnama not in bound:
                if pdefault is not None:
                    bound[pnama] = self._eval_default(
                        pdefault, bound, closure_frame, line)
                else:
                    raise JakselError(
                        "kurang argumen buat '%s', bestie." % unit.nama, line)
        if variadic:
            bound[variadic] = list(args[len(params):])
        return bound

    def _eval_default(self, default_unit, bound, closure_frame, line):
        # default_unit: CodeUnit hasil kompilasi ekspresi default (serializable).
        unit = default_unit
        frames_lama = self.frames
        handlers_lama = self.handlers
        hasil_lama = self._hasil_akhir
        self.frames = []
        self.handlers = []
        try:
            fr = Frame(unit, dict(bound), closure_frame, None, "<default>")
            self.frames.append(fr)
            return self._run()
        finally:
            self.frames = frames_lama
            self.handlers = handlers_lama
            self._hasil_akhir = hasil_lama

    def _dorong_frame(self, fungsi, args, kwargs, line):
        bound = self._ikat_argumen(fungsi.unit, args, kwargs, line,
                                   fungsi._closure)
        frame = Frame(fungsi.unit, bound, fungsi._closure, fungsi,
                      fungsi.unit.nama)
        self.frames.append(frame)

    def _jalankan_fungsi_luar(self, fungsi, args, kwargs):
        """Jalankan FungsiVM di VM ini (dipakai panggil_luar: VM masih kosong).
        Memasang builtins + closure sebagai parent."""
        closure = fungsi._closure
        bound = self._ikat_argumen(fungsi.unit, args, kwargs, None, closure)
        frame = Frame(fungsi.unit, bound, closure, fungsi,
                      fungsi.unit.nama)
        self._install_builtins_ke(frame)
        self.frames.append(frame)
        return self._run()

    def _panggil_nilai_sync(self, fn, args, kwargs, line):
        """Panggil nilai yang BUKAN FungsiVM/_MethodTerikat/kelas (sinkron)."""
        if isinstance(fn, BuiltinFunction):
            if kwargs:
                raise JakselError(
                    "builtin '%s' nggak terima argumen bernama, bestie."
                    % fn.name, line)
            try:
                return fn.func(*args)
            except TypeError:
                raise JakselError(
                    "panggil '%s' argumentnya nggak pas, bestie."
                    % fn.name, line)
        if isinstance(fn, JakselPyCallable):
            if kwargs:
                raise JakselError(
                    "fungsi python nggak terima argumen bernama, bestie.",
                    line)
            try:
                hasil = fn.func(*args)
            except Exception as e:  # noqa: BLE001 - dibungkus
                raise JakselError("error dari Python: %s" % e, line)
            return _py_ke_jaksel(hasil)
        if callable(fn):
            # callable Python biasa
            try:
                return _py_ke_jaksel(fn(*args, **kwargs))
            except JakselError:
                raise
            except Exception as e:  # noqa: BLE001 - dibungkus
                raise JakselError("error dari Python: %s" % e, line)
        raise JakselError("'%s' nggak bisa dipanggil, bestie."
                          % _tname(fn), line)

    def _instansiasi_vm(self, kls, args, kwargs, line):
        """Kelas(args): buat objek; panggil 'lahir' via frame VM."""
        obj = kls.__new__(kls)
        init_fn = None
        for k in kls.__mro__:
            if "__init__" in k.__dict__:
                init_fn = k.__dict__["__init__"]
                break
        if isinstance(init_fn, FungsiVM):
            self._dorong_frame(init_fn, [obj] + list(args), dict(kwargs),
                               line)
            # abaikan nilai balik 'lahir'; yang dipakai obj-nya
            self.frames[-1].nilai_kembali_paksa = obj
        else:
            try:
                if init_fn is not None:
                    init_fn(obj, *args, **kwargs)
                else:
                    _JakselBase.__init__(obj, *args, **kwargs)
            except JakselError:
                raise
            except Exception as e:  # noqa: BLE001 - dibungkus
                raise JakselError("error di 'lahir': %s" % e, line)
            self.frames[-1].stack.append(obj)

    # -- import --

    def _do_import(self, info, frame, line):
        import os as _os
        import importlib as _il
        path, alias, ambil, py_module, baris = info
        if py_module:
            if self.aman:
                raise JakselError(
                    "'collab python' diblokir dalam mode aman (--aman), "
                    "bestie.", line)
            try:
                mod = _il.import_module(py_module)
            except Exception as e:  # noqa: BLE001 - dibungkus
                raise JakselError(
                    "modul python '%s' gagal dimuat: %s" % (py_module, e),
                    line)
            pym = JakselPyModul(py_module, mod)
            if alias:
                frame.define(alias, pym)
            elif ambil:
                for nama in ambil:
                    if not hasattr(mod, nama):
                        raise JakselError(
                            "modul python '%s' nggak punya '%s', bestie."
                            % (py_module, nama), line)
                    frame.define(nama,
                                 JakselPyCallable(getattr(mod, nama), None))
            else:
                frame.define(py_module.split(".")[-1], pym)
            return
        full = path if _os.path.isabs(path) else _os.path.normpath(
            _os.path.join(self.file_dir, path))
        if not full.endswith(".jaksel"):
            full += ".jaksel"
        if not _os.path.isfile(full):
            raise JakselError("modul '%s' nggak ketemu, bestie." % path,
                              line)
        ns = self._modul_cache.get(full)
        if ns is None:
            with open(full, "r", encoding="utf-8") as f:
                src = f.read()
            from .lexer import lex
            from .parser import parse
            from .vm_compiler import Compiler
            unit = Compiler(nama_modul=full).kompilasi_program(
                parse(lex(src, full)))
            sub = VM(aman=self.aman, file_dir=_os.path.dirname(full),
                     prog_args=self.prog_args)
            ns = sub.jalankan_modul(unit)
            # ekspor eksplisit: filter namespace
            ekspor = ns.get("$ekspor")
            if ekspor is not None:
                hilang = [n for n in ekspor if n not in ns]
                if hilang:
                    raise JakselError(
                        "modul '%s' mengekspor %s tapi nama itu nggak ada, "
                        "bestie." % (path, ", ".join(hilang)), line)
                ns = {k: v for k, v in ns.items()
                      if k in ekspor or k.startswith("$")}
            self._modul_cache[full] = ns
        if alias:
            frame.define(alias, _Modul(path, ns))
        elif ambil:
            for nama in ambil:
                if nama not in ns:
                    raise JakselError(
                        "modul '%s' nggak punya '%s', bestie. Yang ada: %s"
                        % (path, nama,
                           ", ".join(sorted(str(k) for k in ns
                                            if not str(k).startswith("$")))
                           or "(kosong)"), line)
                frame.define(nama, ns[nama])
        else:
            for k, v in ns.items():
                if k.startswith("$") or k in self._nama_builtin:
                    continue
                frame.define(k, v)

    # -- eksekusi opcode --

    def _eksekusi(self, frame, op, arg, line):
        st = frame.stack
        unit = frame.unit

        if op == "LOAD_CONST":
            st.append(unit.consts[arg])
        elif op == "POP_TOP":
            st.pop()
        elif op == "DUP_TOP":
            st.append(st[-1])
        elif op == "LOAD_VAR":
            st.append(self._load_var(frame, unit.names[arg], line))
        elif op == "DEF_VAR":
            frame.define(unit.names[arg], st.pop())
        elif op == "STORE_VAR":
            self._store_var(frame, unit.names[arg], st.pop(), line)
        elif op == "BUILD_LIST":
            n = arg
            st.append([st.pop() for _ in range(n)][::-1])
        elif op == "LIST_APPEND":
            val = st.pop()
            st[-1].append(val)
        elif op == "LIST_EXTEND":
            vals = st.pop()
            if not isinstance(vals, (list, tuple)):
                raise JakselError("'...' butuh daftar, bestie.", line)
            st[-1].extend(vals)
        elif op == "BUILD_DICT":
            n = arg
            d = {}
            for _ in range(n):
                v = st.pop()
                k = st.pop()
                d[k] = v
            st.append(d)
        elif op == "DICT_SET":
            v = st.pop()
            k = st.pop()
            st[-1][k] = v
        elif op == "BUILD_STRING":
            n = arg
            bagian = [st.pop() for _ in range(n)][::-1]
            st.append("".join(bagian))
        elif op == "FORMAT":
            st.append(format_value(st.pop()))
        elif op == "BINOP":
            b = st.pop()
            a = st.pop()
            st.append(_binop(unit.names[arg], a, b, line))
        elif op == "CHAIN_COMP":
            # perbandingan berantai: [v0, v1, ...] + tuple op -> bool
            ops = unit.consts[arg]
            n = len(ops)
            vals = [st.pop() for _ in range(n + 1)]
            vals.reverse()
            hasil = True
            for i, nama_op in enumerate(ops):
                if not _binop(nama_op, vals[i], vals[i + 1], line):
                    hasil = False
                    break
            st.append(hasil)
        elif op == "NEG":
            st.append(_neg(st.pop(), line))
        elif op == "NOT":
            st.append(not is_truthy(st.pop()))
        elif op == "JUMP":
            frame.pc = arg
        elif op == "JUMP_IF_FALSE":
            if not is_truthy(st.pop()):
                frame.pc = arg
        elif op == "JUMP_IF_TRUE":
            if is_truthy(st.pop()):
                frame.pc = arg
        elif op == "JUMP_IF_FALSE_OR_POP":
            if not is_truthy(st[-1]):
                frame.pc = arg
            else:
                st.pop()
        elif op == "JUMP_IF_TRUE_OR_POP":
            if is_truthy(st[-1]):
                frame.pc = arg
            else:
                st.pop()
        elif op == "JUMP_IF_NOT_NONE_OR_POP":
            # buat '??': kiri bukan zonk -> lompat (hasil = kiri)
            if st[-1] is not None:
                frame.pc = arg
            else:
                st.pop()
        elif op == "JUMP_IF_NONE":
            # buat '?.': pop nilai, lompat kalo zonk
            if st.pop() is None:
                frame.pc = arg
        elif op == "CALL_FUNC":
            argc = arg
            args = [st.pop() for _ in range(argc)][::-1]
            fn = st.pop()
            self._op_call(frame, fn, args, {}, line)
        elif op == "CALL_FUNC_EX":
            kw = st.pop()
            args = st.pop()
            fn = st.pop()
            self._op_call(frame, fn, list(args), dict(kw), line)
        elif op == "CALL_METHOD":
            name_idx, argc = arg
            args = [st.pop() for _ in range(argc)][::-1]
            obj = st.pop()
            self._op_method(frame, obj, unit.names[name_idx], args, {},
                            line)
        elif op == "CALL_METHOD_OPT":
            # '?.' method call — method hilang = zonk (nggak error)
            name_idx, argc = arg
            args = [st.pop() for _ in range(argc)][::-1]
            obj = st.pop()
            try:
                self._op_method(frame, obj, unit.names[name_idx], args, {},
                                line)
            except JakselError as e:
                if "nggak punya" in str(e):
                    st.append(None)
                else:
                    raise
        elif op == "CALL_METHOD_EX":
            kw = st.pop()
            args = st.pop()
            obj = st.pop()
            self._op_method(frame, obj, unit.names[arg], list(args),
                            dict(kw), line)
        elif op == "SUPER_CALL":
            name_idx, argc = arg
            args = [st.pop() for _ in range(argc)][::-1]
            self._op_super(frame, unit.names[name_idx], args, {}, line)
        elif op == "SUPER_CALL_EX":
            kw = st.pop()
            args = st.pop()
            self._op_super(frame, unit.names[arg], list(args), dict(kw),
                           line)
        elif op == "MAKE_FUNC":
            fn_unit = unit.consts[arg]
            # closure = frame leksikal aktif (referensi hidup)
            f = FungsiVM(fn_unit, frame)
            f._aman = self.aman
            st.append(f)
        elif op == "RETURN":
            self._selesai_frame(frame, st.pop())
        elif op == "THROW":
            raise self._buat_red_flag(st.pop(), line)
        elif op == "SETUP_YOLO":
            self.handlers.append({"frame": frame, "target": arg})
        elif op == "POP_YOLO":
            # pop handler terdalam milik frame ini
            for i in range(len(self.handlers) - 1, -1, -1):
                if self.handlers[i]["frame"] is frame:
                    del self.handlers[i]
                    break
        elif op == "CATCH_VAR":
            exc = st.pop()
            nilai = getattr(exc, "nilai_error", None)
            st.append(nilai if nilai is not None else str(exc))
        elif op == "CATCH_NILAI":
            exc = st.pop()
            st.append(getattr(exc, "nilai_error", None))
        elif op == "MATCH_TYPE":
            kls = st.pop()
            obj = st.pop()
            st.append(_cocok_tipe(obj, kls, "?", line))
        elif op == "MATCH_LIT":
            b = st.pop()
            a = st.pop()
            st.append(a == b and type(a) is type(b))
        elif op == "MATCH_IS_LIST":
            st.append(isinstance(st.pop(), (list, tuple)))
        elif op == "MATCH_DICT_SRC":
            v = st.pop()
            st.append(isinstance(v, (dict, _JakselBase)))
        elif op == "MATCH_ENUM":
            enum_name, member_name = unit.consts[arg]
            st.append(_cocok_enum(st.pop(), enum_name, member_name))
        elif op == "LEN":
            v = st.pop()
            if not isinstance(v, (list, tuple, str, dict)):
                raise JakselError("panjang() cuma buat teks/daftar/kamus.",
                                  line)
            st.append(len(v))
        elif op == "INDEX":
            idx = st.pop()
            obj = st.pop()
            st.append(self._op_index(obj, idx, line))
        elif op == "STORE_INDEX":
            v = st.pop()
            idx = st.pop()
            obj = st.pop()
            self._op_store_index(obj, idx, v, line)
        elif op == "SLICE_FROM":
            idx = st.pop()
            obj = st.pop()
            if not isinstance(obj, (list, tuple)) or not isinstance(idx, int):
                raise JakselError("slice butuh daftar dan angka.", line)
            st.append(list(obj[idx:]))
        elif op == "SLICE":
            langkah = st.pop()
            akhir = st.pop()
            mulai = st.pop()
            obj = st.pop()
            if not isinstance(obj, (list, str)):
                raise JakselError("yang bisa di-slice cuma daftar/teks.", line)
            for nama, v in (("mulai", mulai), ("akhir", akhir),
                            ("langkah", langkah)):
                if v is not None and (isinstance(v, bool)
                                      or not isinstance(v, int)):
                    raise JakselError(
                        "batas slice '%s' harus angka bulat." % nama, line)
            try:
                st.append(obj[mulai:akhir:langkah])
            except Exception:
                raise JakselError("slice gagal, cek batasnya.", line)
        elif op == "LOAD_ATTR":
            obj = st.pop()
            st.append(self._op_load_attr(obj, unit.names[arg], line))
        elif op == "LOAD_ATTR_OPT":
            # '?.' — obj zonk atau atribut hilang = zonk (nggak error)
            obj = st.pop()
            if obj is None:
                st.append(None)
            else:
                try:
                    st.append(self._op_load_attr(obj, unit.names[arg], line))
                except JakselError as e:
                    if "nggak punya" in str(e):
                        st.append(None)
                    else:
                        raise
        elif op == "STORE_ATTR":
            v = st.pop()
            obj = st.pop()
            self._op_store_attr(obj, unit.names[arg], v, line)
        elif op == "DICT_HAS":
            k = st.pop()
            obj = st.pop()
            if isinstance(obj, dict):
                st.append(k in obj)
            elif isinstance(obj, _JakselBase):
                st.append(hasattr(obj, k))
            else:
                st.append(False)
        elif op == "DICT_GET":
            k = st.pop()
            obj = st.pop()
            if isinstance(obj, dict):
                st.append(obj[k])
            elif isinstance(obj, _JakselBase):
                st.append(self._op_load_attr(obj, k, line))
            else:
                raise JakselError("bukan kamus/objek, bestie.", line)
        elif op == "GET_ITER":
            v = st.pop()
            if isinstance(v, dict):
                st.append(iter(list(v.keys())))
            elif isinstance(v, (list, tuple)):
                st.append(iter(list(v)))
            elif isinstance(v, str):
                st.append(iter(list(v)))
            else:
                raise JakselError(
                    "stalk cuma bisa jalanin daftar/teks/kamus, bestie.",
                    line)
        elif op == "FOR_ITER":
            it = st[-1]
            try:
                st.append(next(it))
            except StopIteration:
                st.pop()
                frame.pc = arg
        elif op == "CLASS_BEGIN":
            self._class_ns_stack.append([unit.names[arg], {}])
        elif op == "CLASS_DEF":
            info = unit.consts[arg]  # (nama, is_static)
            nama, is_static = info
            val = st.pop()
            ns = self._class_ns_stack[-1][1]
            if isinstance(val, FungsiVM) and is_static:
                val = _MetodeStatik(val)
            ns[nama] = val
        elif op == "MAKE_PROPERTY":
            setter = st.pop()
            getter = st.pop()
            st.append(_Properti(getter if isinstance(getter, FungsiVM) else None,
                                setter if isinstance(setter, FungsiVM) else None,
                                self.aman))
        elif op == "CLASS_END":
            nama_kls, ns = self._class_ns_stack.pop()
            st.append(self._buat_kelas(nama_kls, ns, st.pop(), line))
        elif op == "BUILD_ENUM":
            nama, pasangan = unit.consts[arg]
            nilai = [st.pop() for _ in range(len(pasangan))][::-1]
            st.append(self._buat_enum(nama, pasangan, nilai, line))
        elif op == "IMPORT":
            self._do_import(unit.consts[arg], frame, line)
        elif op == "EXPORT":
            # 'ekspor a, b' — simpan daftar nama di $ekspor
            names = unit.consts[arg]
            cur = frame.vars.get("$ekspor")
            if cur is None:
                frame.vars["$ekspor"] = list(names)
            else:
                for n in names:
                    if n not in cur:
                        cur.append(n)
        elif op == "EXIT":
            raise _Exit(st.pop())
        else:
            raise JakselError("opcode aneh: %s" % op, line)

    # -- operasi --

    def _op_call(self, frame, fn, args, kwargs, line):
        if isinstance(fn, FungsiVM):
            self._dorong_frame(fn, args, kwargs, line)
        elif isinstance(fn, _MethodTerikat):
            self._dorong_frame(fn.fungsi, [fn.obj] + args, kwargs, line)
        elif isinstance(fn, type) and issubclass(fn, _JakselBase):
            self._instansiasi_vm(fn, args, kwargs, line)
        else:
            frame.stack.append(
                self._panggil_nilai_sync(fn, args, kwargs, line))

    def _op_method(self, frame, obj, nama, args, kwargs, line):
        target = self._cari_method(obj, nama, line)
        if isinstance(target, _MethodTerikat):
            self._dorong_frame(target.fungsi, [target.obj] + args, kwargs,
                               line)
        elif isinstance(target, FungsiVM):
            # statik yang belum di-bind
            self._dorong_frame(target, args, kwargs, line)
        else:
            frame.stack.append(
                self._panggil_nilai_sync(target, args, kwargs, line))

    def _cari_method(self, obj, nama, line):
        """Cari method di objek Jaksel/Python. Kembalikan nilai callable."""
        if isinstance(obj, _JakselBase):
            kls = type(obj)
            # properti (data descriptor di kelas)
            prop = kls.__dict__.get(nama)
            if isinstance(prop, _Properti):
                return prop
            # method di MRO
            for k in kls.__mro__:
                if nama in k.__dict__:
                    m = k.__dict__[nama]
                    if isinstance(m, _MetodeStatik):
                        return m.fungsi
                    if isinstance(m, FungsiVM):
                        return _MethodTerikat(obj, m)
                    if isinstance(m, _Properti):
                        return m
                    # descriptor Python lain / nilai biasa
                    if hasattr(m, "__get__"):
                        return m.__get__(obj, kls)
                    return m
            # atribut instance
            if nama in obj.__dict__:
                return obj.__dict__[nama]
            raise JakselError(
                "'%s' nggak punya '%s', bestie." % (kls.__name__, nama),
                line)
        # kelas enum: Warna.MERAH -> member enum
        if isinstance(obj, type) and issubclass(obj, _EnumBase):
            if nama in obj.__dict__:
                return obj.__dict__[nama]
            raise JakselError(
                "enum '%s' nggak punya '%s', bestie." % (obj.__name__, nama),
                line)
        # kelas biasa: akses statik (Kelas.metode_statik)
        if isinstance(obj, type) and issubclass(obj, _JakselBase):
            for k in obj.__mro__:
                if nama in k.__dict__:
                    m = k.__dict__[nama]
                    if isinstance(m, _MetodeStatik):
                        return m.fungsi
                    if isinstance(m, FungsiVM):
                        return m  # statik: tanpa 'ini'
                    return m
            raise JakselError(
                "kelas '%s' nggak punya '%s', bestie." % (obj.__name__, nama),
                line)
        # modul jaksel: m.tambah -> fungsi di namespace modul
        if isinstance(obj, _Modul):
            if nama in obj.__dict__:
                return obj.__dict__[nama]
            raise JakselError(
                "modul '%s' nggak punya '%s', bestie." % (obj._nama, nama),
                line)
        if isinstance(obj, JakselPyModul):
            if not hasattr(obj.mod, nama):
                raise JakselError(
                    "modul python '%s' nggak punya '%s', bestie."
                    % (obj.nama, nama), line)
            return JakselPyCallable(getattr(obj.mod, nama), None)
        if isinstance(obj, JakselPyObj):
            if not hasattr(obj.obj, nama):
                raise JakselError(
                    "objek python nggak punya '%s', bestie." % nama, line)
            return _py_ke_jaksel(getattr(obj.obj, nama))
        # method bawaan tipe Jaksel (daftar/teks/kamus)
        if isinstance(obj, (list, str, dict)):
            fn = _METHODS.get((type(obj), nama))
            if fn is None:
                if isinstance(obj, dict) and nama in obj:
                    return obj[nama]
                raise JakselError(
                    "%s nggak punya method '%s', bestie."
                    % (_tname(obj), nama), line)
            return _tipe_method(obj, fn)
        raise JakselError("'%s' nggak punya '%s', bestie."
                          % (_tname(obj), nama), line)

    def _op_load_attr(self, obj, nama, line):
        target = self._cari_method(obj, nama, line)
        if isinstance(target, _Properti):
            if target.getter is None:
                raise JakselError(
                    "properti '%s' cuma bisa ditulis, bestie." % nama, line)
            return target.getter.panggil_luar(obj)
        if isinstance(target, _MethodTerikat):
            return target
        return target

    def _op_store_attr(self, obj, nama, val, line):
        if isinstance(obj, _JakselBase):
            kls = type(obj)
            for k in kls.__mro__:
                if nama in k.__dict__:
                    attr = k.__dict__[nama]
                    # _Properti (belum jadi property) atau property Python
                    prop = None
                    if isinstance(attr, _Properti):
                        prop = attr
                    elif isinstance(attr, property):
                        # property dari _Properti.ke_property(): setter ada
                        # di fset (closure panggil_luar)
                        prop = attr
                    if prop is not None:
                        setter = (prop.setter if isinstance(prop, _Properti)
                                  else prop.fset)
                        if setter is None:
                            raise JakselError(
                                "properti '%s' cuma bisa dibaca (nggak ada "
                                "'taruh'), bestie." % nama, line)
                        if isinstance(prop, _Properti):
                            setter.panggil_luar(obj, val)
                        else:
                            try:
                                setter(obj, val)
                            except AttributeError as e:
                                raise JakselError(str(e), line)
                        return
            obj.__dict__[nama] = val
            return
        if isinstance(obj, dict):
            obj[nama] = val
            return
        if isinstance(obj, JakselPyObj):
            try:
                setattr(obj.obj, nama, val)
                return
            except Exception as e:  # noqa: BLE001 - dibungkus
                raise JakselError("gagal set atribut python: %s" % e, line)
        raise JakselError("nggak bisa set atribut di %s, bestie."
                          % _tname(obj), line)

    def _op_index(self, obj, idx, line):
        if isinstance(obj, (list, tuple)):
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise JakselError("index daftar harus angka bulat.", line)
            if idx < 0:
                idx += len(obj)
            if not 0 <= idx < len(obj):
                raise JakselError("index daftar kelewat batas, bestie.",
                                  line)
            return obj[idx]
        if isinstance(obj, dict):
            k = idx if isinstance(idx, str) else str(idx)
            if k not in obj:
                raise JakselError("kunci '%s' nggak ada di kamus, bestie."
                                  % k, line)
            return obj[k]
        if isinstance(obj, str):
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise JakselError("index teks harus angka bulat.", line)
            if idx < 0:
                idx += len(obj)
            if not 0 <= idx < len(obj):
                raise JakselError("index teks kelewat batas, bestie.", line)
            return obj[idx]
        raise JakselError("yang bisa di-index cuma daftar/teks/kamus, "
                          "bestie.", line)

    def _op_store_index(self, obj, idx, val, line):
        if isinstance(obj, list):
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise JakselError("index daftar harus angka bulat.", line)
            if idx < 0:
                idx += len(obj)
            if not 0 <= idx < len(obj):
                raise JakselError("index daftar kelewat batas, bestie.",
                                  line)
            obj[idx] = val
            return
        if isinstance(obj, dict):
            obj[idx if isinstance(idx, str) else str(idx)] = val
            return
        raise JakselError("yang bisa di-index cuma daftar/kamus, bestie.",
                          line)

    def _op_super(self, frame, nama, args, kwargs, line):
        # cari pemilik method di rantai frame
        kls_pemilik = None
        f = frame
        while f is not None:
            if (f.fungsi is not None
                    and f.fungsi._kelas_pemilik is not None):
                kls_pemilik = f.fungsi._kelas_pemilik
                break
            f = f.parent
        if kls_pemilik is None:
            raise JakselError(
                "'ortu' cuma bisa dipakai di dalam method, bestie.", line)
        obj = self._load_var(frame, "ini", line)
        target_name = "__init__" if nama == "lahir" else nama
        target = None
        for k in kls_pemilik.__mro__[1:]:
            if target_name in k.__dict__:
                target = k.__dict__[target_name]
                break
        if target is None:
            raise JakselError(
                "ortu nggak punya '%s', bestie." % nama, line)
        if isinstance(target, FungsiVM):
            self._dorong_frame(target, [obj] + args, kwargs, line)
        elif isinstance(target, _MetodeStatik):
            self._dorong_frame(target.fungsi, args, kwargs, line)
        elif hasattr(target, "__get__"):
            bound = target.__get__(obj, kls_pemilik)
            frame.stack.append(
                self._panggil_nilai_sync(bound, args, kwargs, line))
        else:
            frame.stack.append(
                self._panggil_nilai_sync(target, args, kwargs, line))

    def _buat_red_flag(self, nilai, line):
        if isinstance(nilai, JakselError):
            return nilai
        if isinstance(nilai, _JakselBase) and self._warisi_error(type(nilai)):
            pesan = getattr(nilai, "pesan", None)
            teks = (format_value(pesan) if pesan is not None
                    else format_value(nilai))
            err = JakselError("%s: %s" % (type(nilai).__name__, teks), line)
            err.nilai_error = nilai
        else:
            err = JakselError(format_value(nilai), line)
            err.nilai_error = (nilai if isinstance(nilai, _JakselBase)
                               else None)
        return err

    def _warisi_error(self, kls):
        return isinstance(kls, type) and issubclass(kls, _ErrorJaksel)

    def _buat_kelas(self, nama, ns, basis, line):
        """CLASS_END: rakit type Python dari namespace + basis."""
        if basis is None:
            bases = (_JakselBase,)
        else:
            if not (isinstance(basis, type)
                    and issubclass(basis, _JakselBase)):
                raise JakselError(
                    "yang bisa diwarisi cuma kelas Jaksel, bestie.", line)
            if basis is _ErrorJaksel or issubclass(basis, _ErrorJaksel):
                pass
            bases = (basis,)
        attrs = {}
        for k, v in ns.items():
            if k == "lahir" and isinstance(v, FungsiVM):
                attrs["__init__"] = v
                v._kelas_pemilik = None  # diisi setelah type() jadi
            elif k == "tampil" and isinstance(v, FungsiVM):
                attrs["__repr__"] = _buat_repr(v, self.aman)
            elif isinstance(v, _Properti):
                attrs[k] = v.ke_property()
            elif isinstance(v, _MetodeStatik):
                attrs[k] = v.fungsi  # statik: FungsiVM mentah
            else:
                attrs[k] = v
        kls = type(nama, bases, attrs)
        # tandai pemilik untuk semua method (buat 'ortu')
        for k in kls.__mro__:
            for v in k.__dict__.values():
                if isinstance(v, FungsiVM) and v._kelas_pemilik is None:
                    v._kelas_pemilik = kls
        # cegah warisi melingkar: basis tidak boleh kls itu sendiri
        return kls

    def _buat_enum(self, nama, pasangan, nilai, line):
        attrs = {"_enum_name": nama}
        auto = 0
        for m_nama, m_val in zip(pasangan, nilai):
            if m_val is None:
                v = auto
                auto += 1
            else:
                if not isinstance(m_val, int) or isinstance(m_val, bool):
                    raise JakselError(
                        "nilai enum harus angka bulat, bestie.", line)
                v = m_val
                auto = v + 1
            attrs[m_nama] = _EnumMember(nama, m_nama, v)
        return type(nama, (_EnumBase,), attrs)


