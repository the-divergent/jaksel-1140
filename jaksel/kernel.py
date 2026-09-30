"""Kernel Jupyter buat JakselScript (butuh ipykernel).

Dipasang via:  jaksel kernel pasang
"""

try:
    from ipykernel.kernelbase import Kernel
except ImportError:  # pragma: no cover
    raise SystemExit(
        "butuh 'ipykernel': pip install ipykernel")

from .errors import JakselError, JakselSyntaxError
from .interpreter import Interpreter, _Exit


class JakselKernel(Kernel):
    implementation = "jakselscript"
    implementation_version = "0.6.0"
    language = "jakselscript"
    language_version = "0.6.0"
    language_info = {
        "name": "jakselscript",
        "mimetype": "text/x-jakselscript",
        "file_extension": ".jaksel",
    }
    banner = "JakselScript v0.6.0 — kernel Jupyter, bestie."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.interp = Interpreter()

    def do_execute(self, code, silent, store_history=True,
                   user_expressions=None, allow_stdin=False):
        if not code.strip():
            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}
        try:
            # spill() nulis ke stdout -> otomatis ke-capture jadi output sel
            self.interp.run_source(code, "<sel>", ".")
            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}
        except _Exit:
            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}
        except (JakselError, JakselSyntaxError) as e:
            if not silent:
                self.send_response(self.iopub_socket, "stream",
                                   {"name": "stderr",
                                    "text": e.pretty(code) + "\n"})
            return {"status": "error", "execution_count": self.execution_count,
                    "ename": type(e).__name__, "evalue": str(e),
                    "traceback": [e.pretty(code)]}


if __name__ == "__main__":
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JakselKernel)
