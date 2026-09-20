Attribute VB_Name = "MacCompat_Patch"
'==============================================================================
' SØM v3-4  —  macOS COMPATIBILITY PATCH  (VBA)
'==============================================================================
' Purpose : make the SØM workbook's macros run in Excel for Mac.
' Scope   : the CALCULATION ENGINE is worksheet formulas + pivot tables and
'           already works on Mac WITHOUT macros. The VBA only drives the UI.
'           Only three things are Windows-only and need patching:
'
'   (1) CreateObject("vbscript.regexp")   -> 12 identical helper copies
'   (2) UserForms (HelpInfo, Vælg_visning_res) -> not supported on Mac Excel
'   (3) CreateObject("Word.Application")  -> the two Word-export subs
'
' None of these affect the numbers. (1) is a like-for-like rewrite; (2) and (3)
' are cosmetic (help pop-up, one info box, Word report export) and are simply
' guarded so they no-op on Mac and behave normally on Windows.
'
' IMPORTANT CAVEATS (read before using for anything official):
'   * Work on a COPY. The original is digitally signed; editing the VBA breaks
'     that signature. For numbers you will present to Socialstyrelsen / funders,
'     prefer running the UNMODIFIED, signed model in Windows Excel.
'   * Excel for Mac CANNOT edit or delete UserForm designers. You therefore
'     cannot fully remove the two .frm modules on Mac — instead we (a) stop them
'     being shown and (b) wrap their control-referencing code in #If Not Mac.
'     A 100%-clean removal still needs Windows Excel once.
'   * After patching, VALIDATE: reproduce one official example case and confirm
'     the result cells match the Windows output exactly.
'==============================================================================
'
' This file is documentation + paste-ready code. It is NOT auto-applied.
' Apply the SECTIONS below inside the Excel VBA editor (see APPLY STEPS at end).
'
'==============================================================================
' SECTION A — native regex-free helpers  (behaviour identical to the originals)
'==============================================================================
' Original (Windows-only):
'     Set objRegex = CreateObject("vbscript.regexp")
'     .Pattern = "[^\d]+"  -> CleanString = keep digits only
'     .Pattern = "[0-9]+"  -> CleanNumbers = remove digits, keep the rest
'
' REPLACE the body of EVERY copy of these two functions with the versions
' below. The copies live in these modules (use Edit > Find in the VBE):
'   CleanString : NavigationKnapper, NavigationPile, NavigationRullemenuer,
'                 IndsatsSlet, InfoBox-area, følsomhed_combox, NavigationTrin,
'                 and the HelpInfo form.
'   CleanNumbers: NavigationKnapper, NavigationPile, IndsatsSlet,
'                 følsomhed_combox, NavigationTrin.
' (They are byte-identical, so the same two replacements work everywhere.)

Function CleanString(strIn As String) As String
    ' Keep digits only  (== regex replace "[^\d]+" with "")
    Dim i As Long, ch As String * 1, outp As String
    For i = 1 To Len(strIn)
        ch = Mid$(strIn, i, 1)
        If ch >= "0" And ch <= "9" Then outp = outp & ch
    Next i
    CleanString = outp
End Function

Function CleanNumbers(strIn As String) As String
    ' Remove digits, keep everything else  (== regex replace "[0-9]+" with "")
    Dim i As Long, ch As String * 1, outp As String
    For i = 1 To Len(strIn)
        ch = Mid$(strIn, i, 1)
        If Not (ch >= "0" And ch <= "9") Then outp = outp & ch
    Next i
    CleanNumbers = outp
End Function

'==============================================================================
' SECTION B — info pop-up (HelpInfo UserForm) replaced by a native MsgBox
'==============================================================================
' In module "InfoBox", the original is:
'     Sub info_box()
'         HelpInfo.Show
'     End Sub
' The HelpInfo form merely displayed Range("infotext")(index) for the clicked
' "i" icon. Replace the whole sub with this OS-aware version, which reproduces
' the exact same lookup using a MsgBox on Mac and the original form on Windows.

Sub info_box()
#If Mac Then
    Dim idx As Long
    idx = CleanString(ActiveSheet.Shapes(Application.Caller).Name) * 1
    MsgBox Range("infotext")(idx), vbInformation, "Info"
#Else
    HelpInfo.Show
#End If
End Sub

'==============================================================================
' SECTION C — the "Vælg_visning_res" one-time info box
'==============================================================================
' Find the single caller (in module "Generelt", inside a worksheet-activate
' style routine). The original line is exactly:
'
'     Vælg_visning_res.Show
'
' REPLACE that one line with the guarded block below. On Mac the purely
' informational box is skipped; the surrounding logic (which sets msgbox_res = 2
' and recalculates) is unaffected, so results are identical.
'
'     #If Mac Then
'         ' UserForm not supported on macOS – informational box skipped
'     #Else
'         Vælg_visning_res.Show
'     #End If

'==============================================================================
' SECTION D — Word export (two subs in module "WordEksport")
'==============================================================================
' Add the guard below as the FIRST executable lines of BOTH:
'     Sub Excel_ExportWord()
'     Sub Excel_ExportWord_Skøn()
' i.e. immediately after the Sub ... line and the comment block, BEFORE the
' first "Dim". On Mac it shows a message and exits cleanly; on Windows the
' original Word-automation code runs unchanged.
'
'     #If Mac Then
'         MsgBox "Word-eksport understøttes ikke på macOS." & vbNewLine & _
'                "Brug i stedet Filer > Gem som > PDF, eller kør funktionen " & _
'                "i Excel til Windows.", vbInformation, "SØM"
'         Exit Sub
'     #End If

'==============================================================================
' SECTION E — guarding the UserForm modules themselves (compile safety)
'==============================================================================
' The two form code modules reference MSForms controls (TextBoxInfo, etc.) that
' do not exist on Mac and can break compilation. If the project refuses to
' compile on Mac, wrap the BODY of each routine inside the HelpInfo and
' Vælg_visning_res form modules with conditional compilation so Mac sees an
' empty body, e.g.:
'
'     Private Sub UserForm_Initialize()
'     #If Not Mac Then
'         Dim CallingShapeIndex As Long
'         CallingShapeIndex = CleanString(ActiveSheet.Shapes(Application.Caller).Name) * 1
'         TextBoxInfo.Text = Range("infotext")(CallingShapeIndex)
'     #End If
'     End Sub
'
' Do the same for UserForm_Activate, CmdButton_Ok_Click, OK_knap_Click and
' UserForm_QueryClose. (Editing form code on Mac is limited; if you cannot,
' do this one step in Windows Excel, then the file runs natively on Mac.)
'
'==============================================================================
' APPLY STEPS
'==============================================================================
' 0. Duplicate the file first:  som-v3-4.xlsb  ->  som-v3-4_mac.xlsb
' 1. Open the copy in Excel for Mac.
' 2. Excel menu: Tools > Macro > Visual Basic Editor  (or Option+F11).
' 3. SECTION A: for each module containing CleanString / CleanNumbers, replace
'    the function body with the native version above. (Edit > Find, search for
'    "vbscript.regexp" to jump to each one.)
' 4. SECTION B: replace Sub info_box() in module "InfoBox".
' 5. SECTION C: replace the single "Vælg_visning_res.Show" line.
' 6. SECTION D: add the guard to both subs in module "WordEksport".
' 7. Debug > Compile VBAProject. If it errors only inside the two form modules,
'    apply SECTION E (or do that step once in Windows Excel).
' 8. Save as .xlsb (or .xlsm). Enable macros when prompted.
' 9. VALIDATE: open an official example case and confirm the result cells match
'    the Windows reference output before trusting any figure.
'==============================================================================
