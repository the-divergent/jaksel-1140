# ---------------------------------------------------------------------------
# Compiler: AST JakselScript -> CodeUnit (bytecode)
# ---------------------------------------------------------------------------

from .vm import CodeUnit, JakselError, _parser  # noqa: F401


class Compiler:
    """Mengompilasi AST menjadi CodeUnit siap eksekusi VM."""

    def __init__(self, nama_modul="<utama>"):
        self.nama_modul = nama_modul
        self.unit = None
        self._line = None
        self._loop_stack = []   # {"mulai":pc,"lanjut":pc,"akhir":[patch],"yolo_depth":n}
        self._yolo_stack = []   # [finally Block | None] di fungsi saat ini
        self._tmp = 0

    # -- util --

    def _nama_tmp(self, pref="$t"):
        self._tmp += 1
        return "%s%d" % (pref, self._tmp)

    def _jaga_line(self, node):
        ln = getattr(node, "line", None)
        if ln is not None:
            self._line = ln

    def kompilasi_program(self, prog):
        P = _parser()
        assert isinstance(prog, P.Program), "Compiler butuh Program"
        self.unit = CodeUnit("<utama>")
        for s in prog.statements:
            self.c_stmt(s)
        u = self.unit
        u.emit("LOAD_CONST", u.const(None), line=self._line)
        u.emit("RETURN", line=self._line)
        return self.unit

    def _kompilasi_fungsi(self, node, method=False, statik=False):
        """FuncDef -> CodeUnit. method=True: sisipkan param implisit 'ini'."""
        P = _parser()
        unit_lama, line_lama = self.unit, self._line
        loop_lama, yolo_lama = self._loop_stack, self._yolo_stack
        self._loop_stack, self._yolo_stack = [], []
        try:
            params = list(node.params)
            variadic = node.variadic
            if method and not statik:
                # 'ini' jadi parameter pertama (diikat otomatis saat dipanggil
                # sebagai method). ThisExpr dikompilasi jadi LOAD_VAR "ini".
                params = [("ini", None)] + params
            # Kompilasi default-arg jadi CodeUnit terpisah (serializable,
            # dievaluasi VM saat dipanggil). params: [(nama, unit|None)]
            params_fix = []
            for (pnama, pdefault) in params:
                if pdefault is None:
                    params_fix.append((pnama, None))
                else:
                    du = CodeUnit("<default:%s>" % pnama)
                    du_lama, line_du = self.unit, self._line
                    self.unit, self._line = du, node.line
                    try:
                        self.c_expr(pdefault)
                        du.emit("RETURN")
                    finally:
                        self.unit, self._line = du_lama, line_du
                    params_fix.append((pnama, du))
            unit = CodeUnit(node.name, params=params_fix, variadic=variadic)
            self.unit = unit
            self._line = node.line
            self.c_block(node.body)
            unit.emit("LOAD_CONST", unit.const(None), line=node.line)
            unit.emit("RETURN", line=node.line)
            return unit
        finally:
            self.unit, self._line = unit_lama, line_lama
            self._loop_stack, self._yolo_stack = loop_lama, yolo_lama

    # -- statement --

    def c_block(self, block):
        for s in block.statements:
            self.c_stmt(s)

    def c_stmt(self, node):
        P = _parser()
        u = self.unit
        self._jaga_line(node)
        if isinstance(node, P.VarDecl):
            self._c_vardecl(node)
        elif isinstance(node, P.Assign):
            self._c_assign(node)
        elif isinstance(node, P.ExprStmt):
            self.c_expr(node.expr)
            u.emit("POP_TOP", line=self._line)
        elif isinstance(node, P.IfStmt):
            self._c_if(node)
        elif isinstance(node, P.WhileStmt):
            self._c_while(node)
        elif isinstance(node, P.ForStmt):
            self._c_for(node)
        elif isinstance(node, P.FuncDef):
            unit = self._kompilasi_fungsi(node)
            u.emit("MAKE_FUNC", u.const(unit), line=self._line)
            u.emit("DEF_VAR", u.name(node.name), line=self._line)
        elif isinstance(node, P.ClassDef):
            self._c_classdef(node)
        elif isinstance(node, P.EnumDef):
            self._c_enumdef(node)
        elif isinstance(node, P.ReturnStmt):
            self._c_return(node)
        elif isinstance(node, P.BreakStmt):
            self._c_break()
        elif isinstance(node, P.ContinueStmt):
            self._c_continue()
        elif isinstance(node, P.TryStmt):
            self._c_try(node)
        elif isinstance(node, P.ThrowStmt):
            self.c_expr(node.value)
            u.emit("THROW", line=self._line)
        elif isinstance(node, P.MatchStmt):
            self._c_match(node)
        elif isinstance(node, P.ExitStmt):
            self._c_exit(node)
        elif isinstance(node, P.ImportStmt):
            info = (node.path, node.alias,
                    tuple(node.ambil) if node.ambil else None,
                    node.py_module, node.line)
            u.emit("IMPORT", u.const(info), line=self._line)
        elif isinstance(node, P.ExportStmt):
            u.emit("EXPORT", u.const(tuple(node.names)), line=self._line)
        else:
            raise JakselError(
                "statement aneh: %s" % type(node).__name__, self._line)

    def _c_vardecl(self, node):
        P = _parser()
        u = self.unit
        self.c_expr(node.value)
        if isinstance(node.name, P.Destructure):
            self._c_destructure(node.name, definisikan=True)
        else:
            u.emit("DEF_VAR", u.name(node.name), line=self._line)

    def _c_assign(self, node):
        P = _parser()
        u = self.unit
        tgt = node.target
        if isinstance(tgt, P.Destructure):
            self.c_expr(node.value)
            self._c_destructure(tgt, definisikan=False)
            return
        if isinstance(tgt, P.Name):
            self.c_expr(node.value)
            u.emit("STORE_VAR", u.name(tgt.id), line=self._line)
        elif isinstance(tgt, P.Index):
            self.c_expr(tgt.obj)
            self.c_expr(tgt.index)
            self.c_expr(node.value)
            u.emit("STORE_INDEX", line=self._line)
        elif isinstance(tgt, P.Attr):
            self.c_expr(tgt.obj)
            self.c_expr(node.value)
            u.emit("STORE_ATTR", u.name(tgt.name), line=self._line)
        else:
            raise JakselError("target assignment aneh.", self._line)

    def _c_destructure(self, destr, definisikan):
        """Nilai sudah di stack. definisikan=True -> DEF_VAR, else STORE_VAR."""
        P = _parser()
        u = self.unit
        op_def = "DEF_VAR" if definisikan else "STORE_VAR"
        tmp = self._nama_tmp("$d")
        u.emit("DEF_VAR", u.name(tmp), line=self._line)
        akhir = []
        if destr.kind == "list":
            targets = destr.items
            # cari rest
            idx_rest = next((i for i, t in enumerate(targets)
                             if t.startswith("...")), None)
            n_wajib = idx_rest if idx_rest is not None else len(targets)
            u.emit("LOAD_VAR", u.name(tmp), line=self._line)
            u.emit("MATCH_IS_LIST", line=self._line)
            pos = u.emit("JUMP_IF_FALSE", None, line=self._line)
            gagal = [pos]
            # cek panjang
            u.emit("LOAD_VAR", u.name(tmp), line=self._line)
            u.emit("LEN", line=self._line)
            u.emit("LOAD_CONST", u.const(n_wajib), line=self._line)
            u.emit("BINOP", u.name("==" if idx_rest is None else ">="),
                   line=self._line)
            pos = u.emit("JUMP_IF_FALSE", None, line=self._line)
            gagal.append(pos)
            for i in range(n_wajib):
                u.emit("LOAD_VAR", u.name(tmp), line=self._line)
                u.emit("LOAD_CONST", u.const(i), line=self._line)
                u.emit("INDEX", line=self._line)
                u.emit(op_def, u.name(targets[i]), line=self._line)
            if idx_rest is not None:
                nama_rest = targets[idx_rest][3:]
                u.emit("LOAD_VAR", u.name(tmp), line=self._line)
                u.emit("LOAD_CONST", u.const(n_wajib), line=self._line)
                u.emit("SLICE_FROM", line=self._line)
                u.emit(op_def, u.name(nama_rest), line=self._line)
                for t in targets[idx_rest + 1:]:
                    u.emit("LOAD_CONST", u.const(None), line=self._line)
                    u.emit(op_def, u.name(t), line=self._line)
            akhir.append(u.emit("JUMP", None, line=self._line))
            for pos in gagal:
                u.patch(pos)
            u.emit("LOAD_CONST", u.const(
                "destructuring butuh daftar, bestie."), line=self._line)
            u.emit("THROW", line=self._line)
            for pos in akhir:
                u.patch(pos)
        else:
            # kamus: items = [(kunci, var)]
            u.emit("LOAD_VAR", u.name(tmp), line=self._line)
            u.emit("MATCH_DICT_SRC", line=self._line)
            pos = u.emit("JUMP_IF_FALSE", None, line=self._line)
            gagal = [pos]
            for (kunci, var) in destr.items:
                u.emit("LOAD_VAR", u.name(tmp), line=self._line)
                u.emit("LOAD_CONST", u.const(kunci), line=self._line)
                u.emit("DICT_HAS", line=self._line)
                pos = u.emit("JUMP_IF_FALSE", None, line=self._line)
                gagal.append(pos)
                u.emit("LOAD_VAR", u.name(tmp), line=self._line)
                u.emit("LOAD_CONST", u.const(kunci), line=self._line)
                u.emit("DICT_GET", line=self._line)
                u.emit(op_def, u.name(var), line=self._line)
            akhir.append(u.emit("JUMP", None, line=self._line))
            for pos in gagal:
                u.patch(pos)
            u.emit("LOAD_CONST", u.const(
                "destructuring butuh kamus/objek, bestie."), line=self._line)
            u.emit("THROW", line=self._line)
            for pos in akhir:
                u.patch(pos)

    def _c_if(self, node):
        P = _parser()
        u = self.unit
        self.c_expr(node.cond)
        pos_salah = u.emit("JUMP_IF_FALSE", None, line=self._line)
        self.c_block(node.then_block)
        if node.elifs or node.else_block:
            pos_akhir = [u.emit("JUMP", None, line=self._line)]
            u.patch(pos_salah)
            for (kondisi, blok) in node.elifs:
                self.c_expr(kondisi)
                pos_salah = u.emit("JUMP_IF_FALSE", None, line=self._line)
                self.c_block(blok)
                pos_akhir.append(u.emit("JUMP", None, line=self._line))
                u.patch(pos_salah)
            if node.else_block:
                self.c_block(node.else_block)
            for pos in pos_akhir:
                u.patch(pos)
        else:
            u.patch(pos_salah)

    def _c_while(self, node):
        """gamon: while. 'lanjut' -> lompat ke evaluasi kondisi."""
        u = self.unit
        mulai = len(u.code)
        info = {"mulai": mulai, "lanjut": mulai, "akhir": [],
                "yolo_depth": len(self._yolo_stack), "_patch_lanjut": []}
        self._loop_stack.append(info)
        try:
            self.c_expr(node.cond)
            pos_akhir = u.emit("JUMP_IF_FALSE", None, line=self._line)
            info["akhir"].append(pos_akhir)
            self.c_block(node.body)
            u.emit("JUMP", mulai, line=self._line)
            for pos in info["akhir"]:
                u.patch(pos)
        finally:
            self._loop_stack.pop()

    def _c_for(self, node):
        """stalk x [ , i ] dalam iterable."""
        u = self.unit
        self.c_expr(node.iterable)
        u.emit("GET_ITER", line=self._line)
        cnt = self._nama_tmp("$i")
        u.emit("LOAD_CONST", u.const(0), line=self._line)
        u.emit("DEF_VAR", u.name(cnt), line=self._line)
        mulai = len(u.code)
        info = {"mulai": mulai, "lanjut": None, "akhir": [],
                "yolo_depth": len(self._yolo_stack), "_patch_lanjut": []}
        self._loop_stack.append(info)
        try:
            pos_akhir = u.emit("FOR_ITER", None, line=self._line)
            info["akhir"].append(pos_akhir)
            u.emit("DEF_VAR", u.name(node.var), line=self._line)
            if node.idx_var:
                u.emit("LOAD_VAR", u.name(cnt), line=self._line)
                u.emit("DEF_VAR", u.name(node.idx_var), line=self._line)
            self.c_block(node.body)
            # titik 'lanjut': naikkan penghitung
            lanjut = len(u.code)
            info["lanjut"] = lanjut
            for pos in info["_patch_lanjut"]:
                u.code[pos] = ("JUMP", lanjut)
            u.emit("LOAD_VAR", u.name(cnt), line=self._line)
            u.emit("LOAD_CONST", u.const(1), line=self._line)
            u.emit("BINOP", u.name("+"), line=self._line)
            u.emit("STORE_VAR", u.name(cnt), line=self._line)
            u.emit("JUMP", mulai, line=self._line)
            for pos in info["akhir"]:
                u.patch(pos)
        finally:
            self._loop_stack.pop()

    def _inline_finally_menuju(self, kedalaman_yolo):
        """Emit blok finally untuk yolo di dalam loop target (buat break)."""
        for fb in reversed(self._yolo_stack[kedalaman_yolo:]):
            if fb is not None:
                self.c_block(fb)

    def _c_break(self):
        u = self.unit
        if not self._loop_stack:
            raise JakselError("'ghosting' di luar loop, bestie.", self._line)
        info = self._loop_stack[-1]
        self._inline_finally_menuju(info["yolo_depth"])
        info["akhir"].append(u.emit("JUMP", None, line=self._line))

    def _c_continue(self):
        u = self.unit
        if not self._loop_stack:
            raise JakselError("'lanjut' di luar loop, bestie.", self._line)
        info = self._loop_stack[-1]
        self._inline_finally_menuju(info["yolo_depth"])
        if info["lanjut"] is None:
            # target belum ada (badan for) -> patch nanti
            info["_patch_lanjut"].append(
                u.emit("JUMP", None, line=self._line))
        else:
            u.emit("JUMP", info["lanjut"], line=self._line)

    def _inline_semua_finally(self):
        for fb in reversed(self._yolo_stack):
            if fb is not None:
                self.c_block(fb)

    def _c_return(self, node):
        u = self.unit
        if node.value is not None:
            self.c_expr(node.value)
        else:
            u.emit("LOAD_CONST", u.const(None), line=self._line)
        self._inline_semua_finally()
        u.emit("RETURN", line=self._line)

    def _c_exit(self, node):
        u = self.unit
        if node.code is not None:
            self.c_expr(node.code)
        else:
            u.emit("LOAD_CONST", u.const(0), line=self._line)
        self._inline_semua_finally()
        u.emit("EXIT", line=self._line)

    def _c_try(self, node):
        P = _parser()
        u = self.unit
        pos_setup = u.emit("SETUP_YOLO", None, line=self._line)
        self._yolo_stack.append(node.finally_body)
        try:
            self.c_block(node.body)
        finally:
            self._yolo_stack.pop()
        u.emit("POP_YOLO", line=self._line)
        # blok finally di jalur normal
        if node.finally_body is not None:
            self.c_block(node.finally_body)
        pos_lewat_catch = u.emit("JUMP", None, line=self._line)
        # --- handler exception ---
        u.patch(pos_setup)
        # stack: [exc]
        tmp_e = self._nama_tmp("$e")
        u.emit("DEF_VAR", u.name(tmp_e), line=self._line)
        pos_reraise = []
        if node.catch_class is not None:
            # cocokkan tipe nilai_error terhadap kelas
            u.emit("LOAD_VAR", u.name(tmp_e), line=self._line)
            u.emit("CATCH_NILAI", line=self._line)
            self.c_expr(P.Name(node.catch_class, node.line))
            u.emit("MATCH_TYPE", line=self._line)
            pos_reraise.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
        if node.catch_var is not None:
            u.emit("LOAD_VAR", u.name(tmp_e), line=self._line)
            u.emit("CATCH_VAR", line=self._line)
            u.emit("DEF_VAR", u.name(node.catch_var), line=self._line)
        self.c_block(node.catch_body)
        if node.finally_body is not None:
            self.c_block(node.finally_body)
        pos_lewat_reraise = u.emit("JUMP", None, line=self._line)
        for pos in pos_reraise:
            u.patch(pos)
        # tidak cocok -> lempar ulang (finally tetap jalan)
        u.emit("LOAD_VAR", u.name(tmp_e), line=self._line)
        u.emit("THROW", line=self._line)
        u.patch(pos_lewat_reraise)
        u.patch(pos_lewat_catch)

    def _c_classdef(self, node):
        P = _parser()
        u = self.unit
        if node.parent:
            self.c_expr(P.Name(node.parent, node.line))
        else:
            u.emit("LOAD_CONST", u.const(None), line=self._line)
        u.emit("CLASS_BEGIN", u.name(node.name), line=self._line)
        for m in node.methods:
            if isinstance(m, P.FuncDef):
                unit = self._kompilasi_fungsi(m, method=True,
                                              statik=m.static)
                u.emit("MAKE_FUNC", u.const(unit), line=self._line)
                info = (m.name, bool(m.static))
                u.emit("CLASS_DEF", u.const(info), line=self._line)
            elif isinstance(m, P.PropertyDef):
                self._c_property(m)
            else:
                raise JakselError("member kelas aneh.", self._line)
        u.emit("CLASS_END", line=self._line)
        u.emit("DEF_VAR", u.name(node.name), line=self._line)

    def _c_property(self, node):
        P = _parser()
        u = self.unit
        # getter: talent tanpa param eksplisit (+ 'ini' implisit)
        if node.getter_body is not None:
            getter = P.FuncDef("ambil", [], node.getter_body, node.line)
            unit = self._kompilasi_fungsi(getter, method=True)
            u.emit("MAKE_FUNC", u.const(unit), line=self._line)
        else:
            u.emit("LOAD_CONST", u.const(None), line=self._line)
        if node.setter_body is not None:
            setter = P.FuncDef("taruh", [(node.setter_param, None)],
                               node.setter_body, node.line)
            unit = self._kompilasi_fungsi(setter, method=True)
            u.emit("MAKE_FUNC", u.const(unit), line=self._line)
        else:
            u.emit("LOAD_CONST", u.const(None), line=self._line)
        u.emit("MAKE_PROPERTY", line=self._line)
        info = (node.name, False)
        u.emit("CLASS_DEF", u.const(info), line=self._line)

    def _c_enumdef(self, node):
        u = self.unit
        pasangan = []
        for (nama, vnode) in node.members:
            pasangan.append(nama)
            if vnode is None:
                u.emit("LOAD_CONST", u.const(None), line=self._line)
            else:
                self.c_expr(vnode)
        info = (node.name, tuple(pasangan))
        u.emit("BUILD_ENUM", u.const(info), line=self._line)
        u.emit("DEF_VAR", u.name(node.name), line=self._line)

    # -- pattern matching --

    def _pola_binds(self, pola):
        """Kumpulkan nama variabel yang diikat pola (buat unpacking)."""
        P = _parser()
        if isinstance(pola, P.PatBind):
            return [pola.name]
        if isinstance(pola, P.PatList):
            hasil = []
            for sub in pola.items:
                if isinstance(sub, P.PatBind) and sub.rest:
                    hasil.append(sub.name)
                    break
                hasil.extend(self._pola_binds(sub))
            return hasil
        if isinstance(pola, P.PatDict):
            hasil = []
            for (_k, sub) in pola.items:
                hasil.extend(self._pola_binds(sub))
            return hasil
        return []

    def _c_pola(self, pola, tmp_subjek, gagal):
        """Uji pola thd variabel tmp_subjek. gagal: list patch ke label gagal."""
        P = _parser()
        u = self.unit
        if isinstance(pola, P.PatWild):
            return
        if isinstance(pola, P.PatLit):
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            u.emit("LOAD_CONST", u.const(pola.value), line=self._line)
            u.emit("MATCH_LIT", line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            return
        if isinstance(pola, P.PatBind):
            # $b[nama] = subjek
            u.emit("LOAD_VAR", u.name("$b"), line=self._line)
            u.emit("LOAD_CONST", u.const(pola.name), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            u.emit("STORE_INDEX", line=self._line)
            return
        if isinstance(pola, P.PatType):
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            self.c_expr(P.Name(pola.name, self._line or 0))
            u.emit("MATCH_TYPE", line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            return
        if isinstance(pola, P.PatEnum):
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            info = (pola.enum_name, pola.member_name)
            u.emit("MATCH_ENUM", u.const(info), line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            return
        if isinstance(pola, P.PatList):
            items = pola.items
            idx_rest = next((i for i, s in enumerate(items)
                             if isinstance(s, P.PatBind) and s.rest), None)
            n_wajib = idx_rest if idx_rest is not None else len(items)
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            u.emit("MATCH_IS_LIST", line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            u.emit("LEN", line=self._line)
            u.emit("LOAD_CONST", u.const(n_wajib), line=self._line)
            u.emit("BINOP", u.name("==" if idx_rest is None else ">="),
                   line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            for i in range(n_wajib):
                t = self._nama_tmp("$p")
                u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
                u.emit("LOAD_CONST", u.const(i), line=self._line)
                u.emit("INDEX", line=self._line)
                u.emit("DEF_VAR", u.name(t), line=self._line)
                self._c_pola(items[i], t, gagal)
            if idx_rest is not None:
                u.emit("LOAD_VAR", u.name("$b"), line=self._line)
                u.emit("LOAD_CONST", u.const(items[idx_rest].name),
                       line=self._line)
                u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
                u.emit("LOAD_CONST", u.const(n_wajib), line=self._line)
                u.emit("SLICE_FROM", line=self._line)
                u.emit("STORE_INDEX", line=self._line)
            return
        if isinstance(pola, P.PatDict):
            u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
            u.emit("MATCH_DICT_SRC", line=self._line)
            gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
            for (kunci, sub) in pola.items:
                u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
                u.emit("LOAD_CONST", u.const(kunci), line=self._line)
                u.emit("DICT_HAS", line=self._line)
                gagal.append(u.emit("JUMP_IF_FALSE", None, line=self._line))
                t = self._nama_tmp("$p")
                u.emit("LOAD_VAR", u.name(tmp_subjek), line=self._line)
                u.emit("LOAD_CONST", u.const(kunci), line=self._line)
                u.emit("DICT_GET", line=self._line)
                u.emit("DEF_VAR", u.name(t), line=self._line)
                self._c_pola(sub, t, gagal)
            return
        raise JakselError("pola aneh: %s" % type(pola).__name__, self._line)

    def _kompilasi_arm(self, pola):
        """Satu arm -> CodeUnit fungsi penguji ($s) -> dict ikatan | None."""
        unit_lama, line_lama = self.unit, self._line
        loop_lama, yolo_lama = self._loop_stack, self._yolo_stack
        self._loop_stack, self._yolo_stack = [], []
        try:
            unit = CodeUnit("<pola>", params=[("$s", None)])
            self.unit = unit
            u = unit
            u.emit("BUILD_DICT", 0, line=self._line)
            u.emit("DEF_VAR", u.name("$b"), line=self._line)
            gagal = []
            self._c_pola(pola, "$s", gagal)
            u.emit("LOAD_VAR", u.name("$b"), line=self._line)
            u.emit("RETURN", line=self._line)
            for pos in gagal:
                u.patch(pos)
            u.emit("LOAD_CONST", u.const(None), line=self._line)
            u.emit("RETURN", line=self._line)
            return unit
        finally:
            self.unit, self._line = unit_lama, line_lama
            self._loop_stack, self._yolo_stack = loop_lama, yolo_lama

    def _c_match(self, node):
        u = self.unit
        self.c_expr(node.subject)
        tmp_s = self._nama_tmp("$m")
        u.emit("DEF_VAR", u.name(tmp_s), line=self._line)
        akhir = []
        for (pola, guard, blok) in node.arms:
            arm_unit = self._kompilasi_arm(pola)
            u.emit("MAKE_FUNC", u.const(arm_unit), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_s), line=self._line)
            u.emit("CALL_FUNC", 1, line=self._line)
            # hasil: dict ikatan | None
            u.emit("DUP_TOP", line=self._line)
            u.emit("LOAD_CONST", u.const(None), line=self._line)
            u.emit("BINOP", u.name("!="), line=self._line)
            pos_no = u.emit("JUMP_IF_FALSE", None, line=self._line)
            # cocok: unpack ikatan
            tmp_b = self._nama_tmp("$k")
            u.emit("DEF_VAR", u.name(tmp_b), line=self._line)
            for nama in self._pola_binds(pola):
                u.emit("LOAD_VAR", u.name(tmp_b), line=self._line)
                u.emit("LOAD_CONST", u.const(nama), line=self._line)
                u.emit("INDEX", line=self._line)
                u.emit("DEF_VAR", u.name(nama), line=self._line)
            pos_gg = None
            if guard is not None:
                self.c_expr(guard)
                pos_gg = u.emit("JUMP_IF_FALSE", None, line=self._line)
            self.c_block(blok)
            akhir.append(u.emit("JUMP", None, line=self._line))
            # tidak cocok: buang None
            u.patch(pos_no)
            u.emit("POP_TOP", line=self._line)
            # guard gagal mendarat di sini (stack sudah kosong, tanpa pop)
            if pos_gg is not None:
                u.patch(pos_gg)
        # tidak ada arm yang cocok
        u.emit("LOAD_CONST", u.const(
            "cocokkan: nggak ada pola yang cocok, bestie."), line=self._line)
        u.emit("THROW", line=self._line)
        for pos in akhir:
            u.patch(pos)

    def _c_import(self, node):
        # (ditangani inline di c_stmt via opcode IMPORT)
        pass

    # -- ekspresi --

    def c_expr(self, node):
        P = _parser()
        u = self.unit
        self._jaga_line(node)
        if isinstance(node, P.Literal):
            u.emit("LOAD_CONST", u.const(node.value), line=self._line)
        elif isinstance(node, P.Name):
            u.emit("LOAD_VAR", u.name(node.id), line=self._line)
        elif isinstance(node, P.ThisExpr):
            u.emit("LOAD_VAR", u.name("ini"), line=self._line)
        elif isinstance(node, P.SuperExpr):
            raise JakselError("'ortu' cuma bisa dipakai buat manggil method, "
                              "bestie.", self._line)
        elif isinstance(node, P.InterpString):
            self._c_interp(node)
        elif isinstance(node, P.ListLit):
            for el in node.elements:
                self.c_expr(el)
            u.emit("BUILD_LIST", len(node.elements), line=self._line)
        elif isinstance(node, P.DictLit):
            for (k, v) in node.pairs:
                u.emit("LOAD_CONST", u.const(k), line=self._line)
                self.c_expr(v)
            u.emit("BUILD_DICT", len(node.pairs), line=self._line)
        elif isinstance(node, P.BinOp):
            self._c_binop(node)
        elif isinstance(node, P.UnaryOp):
            self.c_expr(node.operand)
            if node.op == "-":
                u.emit("NEG", line=self._line)
            elif node.op in ("tidak", "!"):
                u.emit("NOT", line=self._line)
            else:
                raise JakselError("operator unary aneh.", self._line)
        elif isinstance(node, P.NotOp):
            self.c_expr(node.operand)
            u.emit("NOT", line=self._line)
        elif isinstance(node, P.Call):
            self._c_call(node)
        elif isinstance(node, P.Attr):
            self.c_expr(node.obj)
            op = "LOAD_ATTR_OPT" if node.optional else "LOAD_ATTR"
            u.emit(op, u.name(node.name), line=self._line)
        elif isinstance(node, P.Index):
            self.c_expr(node.obj)
            self.c_expr(node.index)
            u.emit("INDEX", line=self._line)
        elif isinstance(node, P.Slice):
            self.c_expr(node.obj)
            for v in (node.mulai, node.akhir, node.langkah):
                if v is None:
                    u.emit("LOAD_CONST", u.const(None), line=self._line)
                else:
                    self.c_expr(v)
            u.emit("SLICE", line=self._line)
        elif isinstance(node, P.IfExpr):
            self.c_expr(node.cond)
            pos_else = u.emit("JUMP_IF_FALSE", None, line=self._line)
            self.c_expr(node.then)
            pos_end = u.emit("JUMP", None, line=self._line)
            u.patch(pos_else)
            self.c_expr(node.else_)
            u.patch(pos_end)
        elif isinstance(node, P.ChainComp):
            # 1 < x < 10 — operan dievaluasi sekali, lalu CHAIN_COMP
            self.c_expr(node.first)
            for e in node.operands:
                self.c_expr(e)
            u.emit("CHAIN_COMP", u.const(tuple(node.ops)), line=self._line)
        elif isinstance(node, P.Comp):
            # [expr buat x dalam iter kalo cond] — inline loop.
            # Iterator tinggal di stack selama loop; tiap iterasi
            # mulai & selesai dengan [.., iter].
            tmp_iter = self._nama_tmp("$ci")
            tmp_res = self._nama_tmp("$cr")
            tmp_val = self._nama_tmp("$cv")
            self.c_expr(node.iterable)
            u.emit("GET_ITER", line=self._line)
            u.emit("DEF_VAR", u.name(tmp_iter), line=self._line)
            u.emit("BUILD_LIST", 0, line=self._line)
            u.emit("DEF_VAR", u.name(tmp_res), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_iter), line=self._line)
            mulai = len(u.code)
            pos_akhir = u.emit("FOR_ITER", None, line=self._line)
            u.emit("DEF_VAR", u.name(tmp_val), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_val), line=self._line)
            u.emit("DEF_VAR", u.name(node.var), line=self._line)
            if node.cond is not None:
                self.c_expr(node.cond)
                pos_skip = u.emit("JUMP_IF_FALSE", None, line=self._line)
            else:
                pos_skip = None
            self.c_expr(node.expr)
            u.emit("DEF_VAR", u.name(tmp_val), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_res), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp_val), line=self._line)
            u.emit("LIST_APPEND", line=self._line)
            u.emit("POP_TOP", line=self._line)
            if pos_skip is not None:
                u.patch(pos_skip)
            u.emit("JUMP", mulai, line=self._line)
            u.patch(pos_akhir)
            u.emit("LOAD_VAR", u.name(tmp_res), line=self._line)
        elif isinstance(node, P.Spread):
            raise JakselError("'...' cuma di argumen panggilan.", self._line)
        else:
            raise JakselError(
                "ekspresi aneh: %s" % type(node).__name__, self._line)

    def _c_interp(self, node):
        u = self.unit
        for jenis, bagian in node.parts:
            if jenis == "teks":
                u.emit("LOAD_CONST", u.const(bagian), line=self._line)
            else:
                self.c_expr(bagian)
                u.emit("FORMAT", line=self._line)
        u.emit("BUILD_STRING", len(node.parts), line=self._line)

    def _c_binop(self, node):
        u = self.unit
        if node.op == "dan":
            # short-circuit: kiri falsy -> hasil = kiri (lompat, nilai tetap)
            # kiri truthy -> pop, evaluasi kanan
            self.c_expr(node.left)
            pos = u.emit("JUMP_IF_FALSE_OR_POP", None, line=self._line)
            self.c_expr(node.right)
            u.patch(pos)
            return
        if node.op == "atau":
            # short-circuit: kiri truthy -> hasil = kiri (lompat, nilai tetap)
            # kiri falsy -> pop, evaluasi kanan
            self.c_expr(node.left)
            pos = u.emit("JUMP_IF_TRUE_OR_POP", None, line=self._line)
            self.c_expr(node.right)
            u.patch(pos)
            return
        if node.op == "??":
            # short-circuit: kiri bukan zonk -> hasil = kiri (lompat)
            # kiri zonk -> pop, evaluasi kanan
            self.c_expr(node.left)
            pos = u.emit("JUMP_IF_NOT_NONE_OR_POP", None, line=self._line)
            self.c_expr(node.right)
            u.patch(pos)
            return
        self.c_expr(node.left)
        self.c_expr(node.right)
        u.emit("BINOP", u.name(node.op), line=self._line)

    def _c_call(self, node):
        P = _parser()
        u = self.unit
        args = node.args
        kwargs = node.kwargs  # list[(nama, expr)]
        ada_spread = any(isinstance(a, P.Spread) for a in args)
        is_attr = isinstance(node.func, P.Attr)
        is_super = is_attr and isinstance(node.func.obj, P.SuperExpr)
        is_opt = is_attr and node.func.optional and not is_super

        if is_opt:
            # obj?.method(args): obj zonk -> hasil zonk, args nggak dievaluasi
            tmp = self._nama_tmp("$to")
            self.c_expr(node.func.obj)
            u.emit("DEF_VAR", u.name(tmp), line=self._line)
            u.emit("LOAD_VAR", u.name(tmp), line=self._line)
            pos_none = u.emit("JUMP_IF_NONE", None, line=self._line)
            # jalur tidak-zonk: panggil method normal
            u.emit("LOAD_VAR", u.name(tmp), line=self._line)
            if ada_spread or kwargs:
                # jalur EX disederhanakan: bangun ulang tanpa optional
                # (fallback ke evaluasi normal karena kompleksitas stack)
                pass
            for a in args:
                self.c_expr(a)
            u.emit("CALL_METHOD_OPT", (u.name(node.func.name), len(args)),
                   line=self._line)
            pos_end = u.emit("JUMP", None, line=self._line)
            u.patch(pos_none)
            u.emit("LOAD_CONST", u.const(None), line=self._line)
            u.patch(pos_end)
            return

        if ada_spread or kwargs:
            # ---- jalur EX: bangun daftar argumen & kamus kwargs ----
            if is_super:
                pass  # obj = 'ini' diambil di runtime
            elif is_attr:
                self.c_expr(node.func.obj)
            else:
                self.c_expr(node.func)
            u.emit("BUILD_LIST", 0, line=self._line)
            for a in args:
                if isinstance(a, P.Spread):
                    self.c_expr(a.value)
                    u.emit("LIST_EXTEND", line=self._line)
                else:
                    self.c_expr(a)
                    u.emit("LIST_APPEND", line=self._line)
            u.emit("BUILD_DICT", 0, line=self._line)
            for (knama, kexpr) in kwargs:
                u.emit("LOAD_CONST", u.const(knama), line=self._line)
                self.c_expr(kexpr)
                u.emit("DICT_SET", line=self._line)
            if is_super:
                u.emit("SUPER_CALL_EX", u.name(node.func.name),
                       line=self._line)
            elif is_attr:
                u.emit("CALL_METHOD_EX", u.name(node.func.name),
                       line=self._line)
            else:
                u.emit("CALL_FUNC_EX", line=self._line)
            return

        # ---- jalur cepat ----
        argc = len(args)
        if is_super:
            for a in args:
                self.c_expr(a)
            u.emit("SUPER_CALL", (u.name(node.func.name), argc),
                   line=self._line)
        elif is_attr:
            self.c_expr(node.func.obj)
            for a in args:
                self.c_expr(a)
            u.emit("CALL_METHOD", (u.name(node.func.name), argc),
                   line=self._line)
        else:
            self.c_expr(node.func)
            for a in args:
                self.c_expr(a)
            u.emit("CALL_FUNC", argc, line=self._line)

