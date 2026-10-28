' Abre Poketubi como app de escritorio (ventana propia, sin consola).
' Usa el Python del entorno virtual del proyecto (..\.venv) y, si no existe, el pythonw del sistema.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
py = fso.GetParentFolderName(carpeta) & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(py) Then py = "pythonw"
sh.CurrentDirectory = carpeta
sh.Run """" & py & """ """ & carpeta & "\app_escritorio.pyw""", 0, False
