from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
 QFormLayout, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
 QMessageBox, QPushButton, QSlider, QSplitter, QTabWidget, QTableWidget,
 QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget)
from ...case_reporting import write_case_report
from ...investigation_engine import assess_case

class NewCaseDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent); self.setWindowTitle('Create Investigation')
        f=QFormLayout(self); self.name=QLineEdit(); self.description=QTextEdit(); self.description.setMaximumHeight(100)
        f.addRow('Case name',self.name); f.addRow('Scope / description',self.description)
        b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); b.accepted.connect(self.accept); b.rejected.connect(self.reject); f.addRow(b)

class CasesPage(QWidget):
    def __init__(self,engine,event_bus=None):
        super().__init__(); self.engine=engine; self.event_bus=event_bus; self.timeline_events=[]
        root=QVBoxLayout(self); head=QHBoxLayout(); title=QLabel('Investigation Workspace'); title.setObjectName('pageTitle')
        self.search=QLineEdit(); self.search.setPlaceholderText('Search cases, notes, and evidence…'); self.search.textChanged.connect(self.refresh)
        new=QPushButton('NEW CASE'); new.setObjectName('primary'); new.clicked.connect(self.create_case)
        head.addWidget(title); head.addStretch(); head.addWidget(self.search,1); head.addWidget(new); root.addLayout(head)
        split=QSplitter(Qt.Horizontal); root.addWidget(split,1)
        left=QFrame(); left.setObjectName('panel'); ll=QVBoxLayout(left)
        self.table=QTableWidget(0,5); self.table.setHorizontalHeaderLabels(['ID','CASE','STATUS','SCANS','CREATED']); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.itemSelectionChanged.connect(self.load_case); ll.addWidget(self.table)
        self.scan_choice=QComboBox(); attach=QPushButton('ATTACH SCAN'); attach.clicked.connect(self.attach_scan); row=QHBoxLayout(); row.addWidget(self.scan_choice,1); row.addWidget(attach); ll.addLayout(row); split.addWidget(left)
        right=QFrame(); right.setObjectName('panel'); rl=QVBoxLayout(right); self.case_title=QLabel('SELECT A CASE'); self.case_title.setObjectName('sectionTitle'); rl.addWidget(self.case_title)
        statusrow=QHBoxLayout(); self.status=QComboBox(); self.status.addItems(['OPEN','ACTIVE','REVIEW','CLOSED']); self.status.currentTextChanged.connect(self.change_status); self.ai=QPushButton('RUN AI ANALYSIS'); self.ai.clicked.connect(self.run_ai); statusrow.addWidget(QLabel('STATUS')); statusrow.addWidget(self.status); statusrow.addStretch(); statusrow.addWidget(self.ai); rl.addLayout(statusrow)
        self.tabs=QTabWidget(); rl.addWidget(self.tabs,1)
        self.overview=QTextEdit(); self.overview.setReadOnly(True); self.tabs.addTab(self.overview,'OVERVIEW')
        notes=QWidget(); nl=QVBoxLayout(notes); self.notes_list=QTextEdit(); self.notes_list.setReadOnly(True); self.note=QTextEdit(); self.note.setMaximumHeight(100); self.note.setPlaceholderText('Record observations, next steps, or evidence context…'); save=QPushButton('SAVE NOTE'); save.clicked.connect(self.add_note); nl.addWidget(self.notes_list,1); nl.addWidget(self.note); nl.addWidget(save); self.tabs.addTab(notes,'NOTES')
        ev=QWidget(); el=QVBoxLayout(ev); self.evidence=QTableWidget(0,5); self.evidence.setHorizontalHeaderLabels(['TYPE','TITLE','SOURCE','SHA-256','CREATED']); el.addWidget(self.evidence,1); er=QHBoxLayout(); addtext=QPushButton('ADD TEXT'); addtext.clicked.connect(self.add_text_evidence); addfile=QPushButton('ADD FILE'); addfile.clicked.connect(self.add_file_evidence); shot=QPushButton('CAPTURE WORKSPACE'); shot.clicked.connect(self.capture_workspace); er.addWidget(addtext); er.addWidget(addfile); er.addWidget(shot); er.addStretch(); el.addLayout(er); self.tabs.addTab(ev,'EVIDENCE LOCKER')
        tl=QWidget(); tlayout=QVBoxLayout(tl); self.timeline=QListWidget(); self.replay=QSlider(Qt.Horizontal); self.replay.valueChanged.connect(self.replay_timeline); self.replay_label=QLabel('Timeline replay ready'); tlayout.addWidget(self.timeline,1); tlayout.addWidget(self.replay_label); tlayout.addWidget(self.replay); self.tabs.addTab(tl,'TIMELINE')
        analyst=QWidget(); al=QVBoxLayout(analyst); self.analysis=QTextEdit(); self.analysis.setReadOnly(True); al.addWidget(self.analysis); self.tabs.addTab(analyst,'AI INVESTIGATION')
        ex=QWidget(); xl=QVBoxLayout(ex); xl.addWidget(QLabel('Export the complete case package with scope, scans, notes, evidence hashes, and timeline.')); formats=QHBoxLayout()
        for label,fmt,ext in [('HTML','html','.html'),('PDF','pdf','.pdf'),('MARKDOWN','md','.md'),('JSON','json','.json')]:
            b=QPushButton(label); b.clicked.connect(lambda checked=False,f=fmt,e=ext:self.export_case(f,e)); formats.addWidget(b)
        formats.addStretch(); xl.addLayout(formats); xl.addStretch(); self.tabs.addTab(ex,'EXPORT')
        split.addWidget(right); split.setSizes([520,900]); self.refresh()
    def selected_case_id(self):
        rows=self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return int(self.table.item(rows[0].row(),0).text()) if rows else None
    def refresh(self):
        q=self.search.text().strip() if hasattr(self,'search') else ''
        cases=self.engine.repository.search_cases(q) if q else self.engine.repository.list_cases()
        self.table.setRowCount(len(cases))
        for r,c in enumerate(cases):
            for col,val in enumerate([c['id'],c['name'],c['status'],c['scan_count'],c['created_at'][:19]]): self.table.setItem(r,col,QTableWidgetItem(str(val)))
        current=self.scan_choice.currentData() if hasattr(self,'scan_choice') else None
        self.scan_choice.clear()
        for scan in self.engine.repository.list_recent(150): self.scan_choice.addItem(f"#{scan['id']} {scan['target']} — {scan['open_ports']} open",scan['id'])
        if current:
            i=self.scan_choice.findData(current); self.scan_choice.setCurrentIndex(max(0,i))
        if self.table.rowCount() and self.selected_case_id() is None:
            self.table.selectRow(0)
    def create_case(self):
        d=NewCaseDialog(self)
        if d.exec() and d.name.text().strip():
            cid=self.engine.repository.create_case(d.name.text(),d.description.toPlainText()); self.refresh(); self.select_case(cid)
    def select_case(self,cid):
        for r in range(self.table.rowCount()):
            if int(self.table.item(r,0).text())==cid: self.table.selectRow(r); break
    def load_case(self):
        cid=self.selected_case_id()
        if cid is None:return
        case=next(c for c in self.engine.repository.list_cases() if c['id']==cid); self.case_title.setText(f"CASE #{cid} // {case['name']}")
        self.status.blockSignals(True); self.status.setCurrentText(case['status']); self.status.blockSignals(False)
        scans=self.engine.repository.case_scans(cid); notes=self.engine.repository.case_notes(cid); evidence=self.engine.repository.case_evidence(cid); self.timeline_events=self.engine.repository.case_timeline(cid)
        self.overview.setPlainText(f"SCOPE\n{case['description'] or 'No scope recorded.'}\n\nATTACHED SCANS\n"+'\n'.join(f"#{s['id']} {s['target']} ({s['ip']}) — {s['open_ports']} open ports" for s in scans) if scans else f"SCOPE\n{case['description'] or 'No scope recorded.'}\n\nNo scans attached.")
        self.notes_list.setPlainText('\n\n'.join(f"[{n['created_at'][:19]}]\n{n['note']}" for n in notes) or 'No notes recorded.')
        self.evidence.setRowCount(len(evidence))
        for r,e in enumerate(evidence):
            for col,val in enumerate([e['evidence_type'],e['title'],e['source'] or e['file_path'],e['sha256'][:18]+'…',e['created_at'][:19]]): self.evidence.setItem(r,col,QTableWidgetItem(str(val)))
        self.timeline.clear();
        for e in self.timeline_events:self.timeline.addItem(f"{e['created_at'][11:19]}  {e['event_type']:<9}  {e['title']}")
        self.replay.setMaximum(max(0,len(self.timeline_events)-1)); self.replay.setValue(self.replay.maximum())
    def change_status(self,status):
        cid=self.selected_case_id()
        if cid:self.engine.repository.update_case_status(cid,status); self.refresh(); self.select_case(cid)
    def attach_scan(self):
        cid=self.selected_case_id(); sid=self.scan_choice.currentData()
        if cid and sid:self.engine.repository.attach_scan_to_case(cid,int(sid)); self.load_case()
    def add_note(self):
        cid=self.selected_case_id(); text=self.note.toPlainText().strip()
        if cid and text:self.engine.repository.add_case_note(cid,text); self.note.clear(); self.load_case()
    def add_text_evidence(self):
        cid=self.selected_case_id()
        if not cid:return
        d=QDialog(self); d.setWindowTitle('Add Text Evidence'); f=QFormLayout(d); kind=QComboBox(); kind.addItems(['OBSERVATION','WHOIS','DNS','HEADERS','AI','LOG','OTHER']); title=QLineEdit(); source=QLineEdit(); content=QTextEdit(); f.addRow('Type',kind); f.addRow('Title',title); f.addRow('Source',source); f.addRow('Content',content); b=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); b.accepted.connect(d.accept); b.rejected.connect(d.reject); f.addRow(b)
        if d.exec() and title.text().strip(): self.engine.repository.add_case_evidence(cid,kind.currentText(),title.text(),source.text(),content.toPlainText()); self.load_case()
    def add_file_evidence(self):
        cid=self.selected_case_id(); path,_=QFileDialog.getOpenFileName(self,'Add Evidence File')
        if cid and path:self.engine.repository.add_case_evidence(cid,'FILE',Path(path).name,path,'',path); self.load_case()
    def capture_workspace(self):
        cid=self.selected_case_id()
        if not cid:return
        folder=Path.home()/'.blackterm-recon'/'evidence'/f'case_{cid}'; folder.mkdir(parents=True,exist_ok=True); path=folder/'workspace.png'; self.window().grab().save(str(path),'PNG'); self.engine.repository.add_case_evidence(cid,'SCREENSHOT','BLACKTERM workspace capture','desktop','',str(path)); self.load_case()
    def run_ai(self):
        cid = self.selected_case_id()
        if not cid:
            return
        self.ai.setEnabled(False)
        self.ai.setText("ANALYZING…")
        try:
            assessment = assess_case(self.engine.repository, cid)
            text = assessment.to_text()
            self.analysis.setPlainText(text)
            self.engine.repository.add_case_evidence(
                cid, "AI", "AI investigation summary", "BLACKTERM AI", text
            )
            self.engine.repository.add_case_timeline(
                cid, "AI", "AI investigation completed",
                f"{assessment.level} risk / {assessment.confidence}% confidence",
            )
            if self.event_bus:
                from ...events import EventLevel
                self.event_bus.emit(
                    "case",
                    f"Case #{cid}: {assessment.summary}",
                    title="AI Case Analysis Complete",
                    level=EventLevel.AI,
                    module="cases",
                    metadata={"case_id": cid, "score": assessment.score,
                              "risk": assessment.level,
                              "confidence": assessment.confidence},
                )
            self.load_case()
            self.analysis.setPlainText(text)
            self.tabs.setCurrentIndex(4)
        finally:
            self.ai.setEnabled(True)
            self.ai.setText("RUN AI ANALYSIS")
    def replay_timeline(self,index):
        if not self.timeline_events:return
        index=min(index,len(self.timeline_events)-1)
        for i in range(self.timeline.count()):self.timeline.item(i).setHidden(i>index)
        e=self.timeline_events[index]; self.replay_label.setText(f"Replay {index+1}/{len(self.timeline_events)} — {e['event_type']}: {e['title']}")
    def export_case(self,fmt,ext):
        cid=self.selected_case_id()
        if not cid:return
        path,_=QFileDialog.getSaveFileName(self,'Export Case',f'blackterm_case_{cid}{ext}')
        if path:
            try: out=write_case_report(self.engine.repository,cid,path,fmt); QMessageBox.information(self,'Case exported',str(out))
            except Exception as exc: QMessageBox.critical(self,'Export failed',str(exc))
