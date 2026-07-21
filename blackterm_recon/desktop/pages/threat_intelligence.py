from __future__ import annotations
import json
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import QCheckBox,QFrame,QGridLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QMessageBox,QProgressBar,QPushButton,QSplitter,QTabWidget,QTextEdit,QVBoxLayout,QWidget
from ...threat_intelligence import persist_threat_run
from ..threat_worker import ThreatIntelligenceWorker
from ..widgets import add_glow

PROVIDERS=(("local","Local Analysis"),("urlhaus","URLhaus"),("virustotal","VirusTotal"),("abuseipdb","AbuseIPDB"))

class MetricCard(QFrame):
    def __init__(self,label):
        super().__init__(); self.setObjectName("panel"); add_glow(self,blur=14,alpha=20)
        l=QVBoxLayout(self); t=QLabel(label); t.setObjectName("muted"); self.value=QLabel("--"); self.value.setObjectName("metricValue"); self.value.setWordWrap(True); l.addWidget(t); l.addWidget(self.value)
    def set_value(self,v): self.value.setText(str(v).strip() if v is not None and str(v).strip() else "--")

class ThreatIntelligencePage(QWidget):
    case_created=Signal(int)
    def __init__(self,engine,event_bus=None,parent=None):
        super().__init__(parent); self.engine=engine; self.event_bus=event_bus; self.thread=None; self.worker=None; self.current_result=None; self.current_case_id=None
        root=QVBoxLayout(self)
        h=QHBoxLayout(); titles=QVBoxLayout(); title=QLabel("THREAT INTELLIGENCE CENTER"); title.setObjectName("pageTitle"); sub=QLabel("Source-aware IOC reputation, provider correlation, confidence scoring, and case evidence."); sub.setObjectName("muted"); titles.addWidget(title); titles.addWidget(sub); h.addLayout(titles); h.addStretch(); self.status=QLabel("● READY"); self.status.setObjectName("liveReady"); h.addWidget(self.status); root.addLayout(h)
        launch=QFrame(); launch.setObjectName("intelligenceLaunch"); ll=QVBoxLayout(launch); row=QHBoxLayout(); self.target=QLineEdit(); self.target.setPlaceholderText("domain, public IP address, or authorized URL"); self.target.returnPressed.connect(self.start_collection); self.run_button=QPushButton("ANALYZE THREAT"); self.run_button.setObjectName("primary"); self.run_button.clicked.connect(self.start_collection); row.addWidget(QLabel("INDICATOR")); row.addWidget(self.target,1); row.addWidget(self.run_button); ll.addLayout(row)
        prow=QHBoxLayout(); self.checks={}
        for key,label in PROVIDERS:
            c=QCheckBox(label); c.setChecked(True); self.checks[key]=c; prow.addWidget(c)
        prow.addStretch(); ll.addLayout(prow); pr=QHBoxLayout(); self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress_label=QLabel("PIPELINE READY"); pr.addWidget(self.progress,1); pr.addWidget(self.progress_label); ll.addLayout(pr); root.addWidget(launch)
        metrics=QGridLayout(); self.score=MetricCard("THREAT SCORE"); self.verdict=MetricCard("VERDICT"); self.confidence=MetricCard("CONFIDENCE"); self.matches=MetricCard("IOC MATCHES"); self.cves=MetricCard("CVE MATCHES"); self.feeds=MetricCard("PROVIDERS ONLINE")
        for i,c in enumerate((self.score,self.verdict,self.confidence,self.matches,self.cves,self.feeds)): metrics.addWidget(c,i//3,i%3)
        root.addLayout(metrics)
        split=QSplitter(Qt.Horizontal); root.addWidget(split,1)
        left=QFrame(); left.setObjectName("panel"); lv=QVBoxLayout(left); lv.addWidget(QLabel("PROVIDER PIPELINE")); self.provider_list=QListWidget(); lv.addWidget(self.provider_list,1); lv.addWidget(QLabel("ANALYSIS LOG")); self.console=QTextEdit(); self.console.setReadOnly(True); self.console.setMaximumHeight(190); lv.addWidget(self.console); split.addWidget(left)
        right=QFrame(); right.setObjectName("panel"); rv=QVBoxLayout(right); self.tabs=QTabWidget(); self.summary=QTextEdit(); self.findings=QTextEdit(); self.evidence=QTextEdit(); self.raw=QTextEdit()
        for w in (self.summary,self.findings,self.evidence,self.raw): w.setReadOnly(True)
        self.tabs.addTab(self.summary,"ASSESSMENT"); self.tabs.addTab(self.findings,"FINDINGS"); self.tabs.addTab(self.evidence,"SOURCES / EVIDENCE"); self.tabs.addTab(self.raw,"RAW JSON"); rv.addWidget(self.tabs,1)
        actions=QHBoxLayout(); self.save_case=QPushButton("SAVE TO CASE"); self.save_case.setEnabled(False); self.save_case.clicked.connect(self.persist_case); self.copy_report=QPushButton("COPY REPORT"); self.copy_report.setEnabled(False); self.copy_report.clicked.connect(self.copy_report_text); actions.addWidget(self.save_case); actions.addWidget(self.copy_report); actions.addStretch(); rv.addLayout(actions); split.addWidget(right); split.setSizes([430,850]); self._reset()
    def _reset(self):
        self.provider_list.clear()
        for _,label in PROVIDERS: self.provider_list.addItem(f"○  {label:<18} WAITING")
    def start_collection(self):
        target=self.target.text().strip()
        if not target: QMessageBox.warning(self,"Threat Intelligence","Enter a domain, public IP address, or URL."); return
        if self.thread is not None: return
        enabled=tuple(k for k,_ in PROVIDERS if self.checks[k].isChecked())
        if not enabled: QMessageBox.warning(self,"Threat Intelligence","Select at least one provider."); return
        self.current_result=None; self.current_case_id=None; self.progress.setValue(0); self.progress_label.setText("STARTING"); self.status.setText("● ANALYZING"); self.run_button.setEnabled(False); self.save_case.setEnabled(False); self.copy_report.setEnabled(False); self.console.clear(); self.summary.clear(); self.findings.clear(); self.evidence.clear(); self.raw.clear(); self._reset()
        for c in (self.score,self.verdict,self.confidence,self.matches,self.cves,self.feeds): c.set_value("--")
        self.thread=QThread(self); self.worker=ThreatIntelligenceWorker(target,enabled,self.engine.config); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.on_progress); self.worker.completed.connect(self.on_completed); self.worker.failed.connect(self.on_failed); self.worker.finished.connect(self.thread.quit); self.worker.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self._thread_finished); self.thread.start()
    def on_progress(self,provider,percent,message,result):
        self.progress.setValue(percent); self.progress_label.setText(f"{percent}% // {provider.upper()}"); self.console.append(f"[{percent:>3}%] {provider.upper():<14} {message}")
        keys=[k for k,_ in PROVIDERS]
        if provider in keys:
            i=keys.index(provider); label=PROVIDERS[i][1]; state="RUNNING" if result is None else str(getattr(result,"status","complete")).upper(); icon="◉" if result is None else "✓" if state=="SUCCESS" else "–" if state=="SKIPPED" else "!"; self.provider_list.item(i).setText(f"{icon}  {label:<18} {state}")
    def on_completed(self,result):
        self.current_result=result; self.progress.setValue(100); self.progress_label.setText("ANALYSIS COMPLETE"); self.status.setText("● COMPLETE"); self.save_case.setEnabled(True); self.copy_report.setEnabled(True); self._render(result)
    def on_failed(self,message): self.status.setText("● ERROR"); self.progress_label.setText("PIPELINE ERROR"); QMessageBox.critical(self,"Threat analysis failed",message)
    def _thread_finished(self): self.thread=None; self.worker=None; self.run_button.setEnabled(True)
    def _render(self,r):
        self.score.set_value(f"{r.level} // {r.threat_score}/100"); self.verdict.set_value(r.verdict); self.confidence.set_value(f"{r.confidence}%"); self.matches.set_value(r.ioc_matches); self.cves.set_value(r.cve_matches); self.feeds.set_value(f"{sum(1 for p in r.providers if p.status=='success')}/{len(r.providers)}")
        self.summary.setPlainText(r.to_text()); self.findings.setPlainText("\n\n".join(f"[{f.severity}] {f.title}\n{f.detail}\nSource: {f.source} // Confidence: {f.confidence}%" for f in r.findings) or "No high-signal findings were produced.")
        self.evidence.setPlainText("\n\n".join(f"{e.evidence_type} // {e.title}\nSOURCE: {e.source}\n{e.content[:1600]}" for e in r.evidence) or "No provider evidence was collected."); self.raw.setPlainText(json.dumps(r.to_dict(),indent=2,default=str))
    def persist_case(self):
        if self.current_result is None:return
        try:
            if self.current_case_id is None:self.current_case_id=persist_threat_run(self.engine.repository,self.current_result)
            self.save_case.setText(f"CASE #{self.current_case_id} SAVED"); self.save_case.setEnabled(False); self.case_created.emit(self.current_case_id); QMessageBox.information(self,"Threat case created",f"Threat intelligence was saved to case #{self.current_case_id}.")
        except Exception as exc: QMessageBox.critical(self,"Case persistence failed",str(exc))
    def copy_report_text(self):
        if self.current_result is None:return
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.current_result.to_text()); self.copy_report.setText("COPIED")
