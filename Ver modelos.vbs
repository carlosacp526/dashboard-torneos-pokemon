' Abre el visor de modelos (ficha tecnica de cada modelo de ML) sin ventana de consola.
' Usa el Python del entorno virtual del proyecto (..\.venv) y, si no existe, el pythonw del sistema.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
py = fso.GetParentFolderName(carpeta) & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(py) Then py = "pythonw"
sh.CurrentDirectory = carpeta
sh.Run """" & py & """ """ & carpeta & "\visor_modelos.pyw""", 0, False
