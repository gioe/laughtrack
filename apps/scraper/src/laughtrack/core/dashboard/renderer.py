"""High-level HTML assembly for the dashboard."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from .builders import (
    build_recent_sessions_html,
    build_error_details_rows,
    build_db_operations_rows,
    build_dedup_widget_html,
    build_sessions_payload,
)


def render_full_html(sessions: List[Dict[str, Any]]) -> str:
    latest = sessions[0] if sessions else {}
    recent_rows = build_recent_sessions_html(sessions)
    if latest:
        snap = latest.get("snapshot")
    else:
        snap = None
    error_rows = build_error_details_rows((snap.error_details if snap else []))
    db_rows = build_db_operations_rows(latest) if latest else ""
    dedup_widget = build_dedup_widget_html(latest) if latest else ""
    sessions_payload = json.dumps(build_sessions_payload(sessions))
    # Trends currently disabled (single snapshot view).
    html = """<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/><title>Scraper Metrics Dashboard</title><style>body { font-family: system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif; margin:0; padding:24px; background:#f6f8fa;}h1{margin-top:0;}table{border-collapse:collapse;width:100%;}th,td{padding:6px 8px;border:1px solid #e1e4e8;font-size:0.85rem;}tr.success{background:#f0fff4;}tr.error{background:#fff5f5;}.section{background:#fff;border:1px solid #e1e4e8;border-radius:8px;padding:16px;margin-bottom:24px;box-shadow:0 1px 2px rgba(0,0,0,0.04);} .muted{color:#666;}.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;}@media (max-width:1000px){.grid{grid-template-columns:1fr;}}code{background:#f3f4f6;padding:2px 4px;border-radius:4px;}#club-filter-bar label{font-size:0.9rem;}#club-filter-bar select{padding:4px 8px;border-radius:6px;border:1px solid #d0d7de;background:#fff;}#club-filter-bar{display:none;align-items:center;gap:12px;} .mc-value{font-weight:600;color:#111827;}</style></head><body><h1>Scraper Metrics Dashboard</h1><p class='muted'>Sessions: __SESS_COUNT__</p><div class='section' id='club-filter-bar'><div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'><label for='club-select'><strong>Club:</strong></label><select id='club-select'><option value=''>All Clubs</option></select><span id='club-summary' class='muted'></span></div></div><div class='section'><h2>Recent Sessions</h2><table><thead><tr><th>Datetime</th><th>Scraped</th><th>Saved</th><th>Inserted</th><th>Updated</th><th>Failed</th><th>Clubs</th><th>Errors</th><th>Skipped</th><th>Validation</th><th>DB Errors</th><th>Success %</th></tr></thead><tbody>__RECENT_ROWS__</tbody></table></div><div class='grid'><div class='section'><h2>Latest Error Details</h2><table id='error-details-table'><thead><tr><th>Club</th><th>Error</th></tr></thead><tbody>__ERROR_ROWS__</tbody></table></div><div class='section'><h2>Latest DB Operations</h2><table><thead><tr><th>Operation</th><th>Count</th><th>Status</th></tr></thead><tbody>__DB_ROWS__</tbody></table></div></div><div class='section'><h2>Deduplicated Shows</h2>__DEDUP__</div><script>window.DASHBOARD_SESSIONS=__SESSIONS_JSON__;</script><script>(function(){const s=window.DASHBOARD_SESSIONS||[];if(!s.length)return;const l=s[0];if(!l||!l.clubs||!l.clubs.length)return;const bar=document.getElementById('club-filter-bar');const sel=document.getElementById('club-select');const summary=document.getElementById('club-summary');const errTable=document.getElementById('error-details-table');const errRows=errTable?Array.from(errTable.querySelectorAll('tbody tr')):[];const uniq=[];l.clubs.forEach(c=>{const id=(c.club_id!=null?String(c.club_id):'');const name=c.club||'';if(!id)return; if(!uniq.find(x=>x.id===id)){uniq.push({id,name});}});uniq.sort((a,b)=>a.name.localeCompare(b.name)).forEach(o=>{const opt=document.createElement('option');opt.value=o.id;opt.textContent=o.name;opt.setAttribute('data-name',o.name);sel.appendChild(opt);});bar.style.display='block';function fc(id){return l.clubs.find(c=>String(c.club_id)===String(id));}function upd(){const id=sel.value;if(id){const c=fc(id)||{};const sr=c.success_rate!=null?Number(c.success_rate).toFixed(1)+'%':'-';const name=c.club||'(unknown)';summary.textContent=`${name} (#${id}) — shows: ${(c.num_shows||0).toLocaleString()} saved: ${(c.saved||0).toLocaleString()} inserted: ${(c.inserted||0).toLocaleString()} updated: ${(c.updated||0).toLocaleString()} failed_saves: ${(c.failed_saves||0).toLocaleString()} errors: ${(c.errors||0).toLocaleString()} success: ${sr}`;} else summary.textContent='';if(errRows.length){errRows.forEach(r=>{if(!id){r.style.display='';return;}const cell=r.children[0];const cc=cell?cell.textContent.trim():'';const rowMatches=cc && cc.indexOf('#')>-1 ? cc.split('#').pop().replace(/[^0-9].*$/,'')===id : cc===id; r.style.display=rowMatches?'':'none';});}if(window.DEDUP_WIDGET){if(typeof window.DEDUP_WIDGET.setClubId==='function'){window.DEDUP_WIDGET.setClubId(id);}else if(typeof window.DEDUP_WIDGET.setClubName==='function'){window.DEDUP_WIDGET.setClubName(id);}} (window.__CLUB_SELECTION_LISTENERS||[]).forEach(fn=>{try{fn(id);}catch(e){}});} sel.addEventListener('change',upd); window.__CLUB_SELECTION_LISTENERS=window.__CLUB_SELECTION_LISTENERS||[]; upd();})();</script></body></html>"""
    html = (
        html.replace("__SESS_COUNT__", str(len(sessions)))
        .replace("__RECENT_ROWS__", recent_rows)
        .replace("__ERROR_ROWS__", error_rows)
        .replace("__DB_ROWS__", db_rows)
        .replace("__DEDUP__", dedup_widget)
        .replace("__SESSIONS_JSON__", sessions_payload)
    )
    return html
