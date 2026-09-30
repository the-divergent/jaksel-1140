// Client LSP JakselScript untuk VS Code.
// Nyalakan server bahasa (diagnostics, hover, completion) via stdio:
//   jaksel lsp
// Path executable bisa diubah di settings: jakselscript.serverPath

const vscode = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client = null;

function activate(context) {
    const config = vscode.workspace.getConfiguration("jakselscript");
    const serverPath = config.get("serverPath", "jaksel");

    const serverOptions = {
        command: serverPath,
        args: ["lsp"],
        transport: TransportKind.stdio,
    };
    const clientOptions = {
        documentSelector: [{ scheme: "file", language: "jaksel" }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher("**/.jaksel"),
        },
    };

    client = new LanguageClient(
        "jakselscript-lsp",
        "JakselScript Language Server",
        serverOptions,
        clientOptions
    );
    client.start();
    context.subscriptions.push(
        vscode.commands.registerCommand("jakselscript.restartServer", async () => {
            await client.stop();
            client.start();
            vscode.window.showInformationMessage("JakselScript LSP direstart, bestie.");
        })
    );
}

function deactivate() {
    if (client) {
        return client.stop();
    }
}

module.exports = { activate, deactivate };
