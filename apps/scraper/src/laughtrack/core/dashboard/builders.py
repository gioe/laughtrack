"""HTML/data fragment builders for the dashboard.

Separated from rendering so they can be unit tested in isolation later.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List
from dataclasses import asdict

from laughtrack.core.models.metrics import ScrapingMetricsSnapshot


def build_recent_sessions_html(metrics: List[Dict[str, Any]]) -> str:
    rows = []
    for session in metrics[:10]:  # last 10
        dt = session["datetime"]
        snap: ScrapingMetricsSnapshot = session["snapshot"]
        shows_block = snap.shows
        errors_block = snap.errors
        clubs_block = snap.clubs
        shows = shows_block.scraped
        saved = shows_block.saved
        inserted = shows_block.inserted
        updated = shows_block.updated
        failed_saves = shows_block.failed_save
        skipped = shows_block.skipped_dedup
        validation = shows_block.validation_failed
        db_err = shows_block.db_errors
        errors = errors_block.total
        clubs = clubs_block.processed
        success_rate = float(snap.success_rate or 0.0)
        status_class = "success" if errors == 0 and failed_saves == 0 else "error"
        status_emoji = "✅" if errors == 0 and failed_saves == 0 else "❌"
        rows.append(
            f"""
        <tr class=\"{status_class}\">
            <td>{status_emoji} {dt.strftime('%Y-%m-%d %H:%M:%S')}</td>
            <td>{shows:,}</td>
            <td>{saved:,}</td>
            <td>{inserted:,}</td>
            <td>{updated:,}</td>
            <td>{failed_saves:,}</td>
            <td>{clubs}</td>
            <td>{errors}</td>
            <td>{skipped:,}</td>
            <td>{validation:,}</td>
            <td>{db_err:,}</td>
            <td>{success_rate:.1f}%</td>
        </tr>
        """
        )
    return "".join(rows)


def build_sessions_payload(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sessions_payload: List[Dict[str, Any]] = []
    for session in metrics:
        dt = session["datetime"]
        snap: ScrapingMetricsSnapshot = session["snapshot"]
        err_by_club: Dict[str, List[str]] = {}
        for ed in snap.error_details or []:
            c = ed.club or "Unknown"
            err_by_club.setdefault(c, []).append(ed.error or "")

        clubs_list = []
        club_stats_iter = snap.per_club_stats or []
        for s in club_stats_iter:
            club_name = s.club or "Unknown"
            clubs_list.append(
                {
                    "club": club_name,
                    "club_id": s.club_id,
                    "num_shows": int(s.num_shows or 0),
                    "status": "error" if s.error else "success",
                    "error": s.error,
                    "saved": s.saved,
                    "inserted": s.inserted,
                    "updated": s.updated,
                    "failed_saves": s.failed_saves,
                    "errors": s.errors,
                    "success_rate": s.success_rate,
                    "skipped_dedup": s.skipped_dedup,
                    "validation_failed": s.validation_failed,
                    "db_errors": s.db_errors,
                    "error_details": err_by_club.get(club_name, []),
                    "http_status": s.http_status,
                    "bot_block_detected": s.bot_block_detected,
                    "bot_block_signature": s.bot_block_signature,
                    "bot_block_provider": s.bot_block_provider,
                    "bot_block_type": s.bot_block_type,
                    "bot_block_source": s.bot_block_source,
                    "bot_block_stage": s.bot_block_stage,
                    "playwright_fallback_used": s.playwright_fallback_used,
                    "items_before_filter": s.items_before_filter,
                }
            )
        known = {c["club"] for c in clubs_list}
        for club_name, msgs in err_by_club.items():
            if club_name not in known:
                clubs_list.append(
                    {
                        "club": club_name,
                        "club_id": None,
                        "num_shows": 0,
                        "status": "error",
                        "error": None,
                        "saved": None,
                        "inserted": None,
                        "updated": None,
                        "failed_saves": None,
                        "errors": len(msgs),
                        "success_rate": None,
                        "skipped_dedup": None,
                        "validation_failed": None,
                        "db_errors": None,
                        "error_details": msgs,
                        "http_status": None,
                        "bot_block_detected": False,
                        "bot_block_signature": None,
                        "bot_block_provider": None,
                        "bot_block_type": None,
                        "bot_block_source": None,
                        "bot_block_stage": None,
                        "playwright_fallback_used": False,
                        "items_before_filter": None,
                    }
                )
        totals = {
            "scraped": snap.shows.scraped,
            "saved": snap.shows.saved,
            "inserted": snap.shows.inserted,
            "updated": snap.shows.updated,
            "failed_saves": snap.shows.failed_save,
            "errors": snap.errors.total,
            "clubs": snap.clubs.processed,
            "success_rate": float(snap.success_rate or 0.0),
            "skipped_dedup": snap.shows.skipped_dedup,
            "validation_failed": snap.shows.validation_failed,
            "db_errors": snap.shows.db_errors,
        }
        sessions_payload.append({
            "id": dt.isoformat(),
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "totals": totals,
            "clubs": clubs_list,
        })
    return sessions_payload


def build_chart_data(metrics: List[Dict[str, Any]]):
    """Return chart series for the most recent 20 sessions (chronological).

    We store sessions in descending order (newest first). The previous
    implementation incorrectly used the oldest 20 sessions (metrics[-20:]).
    This now selects the newest 20 (metrics[:20]) and reverses them so the
    chart plots left→right in time order.
    """
    recent = metrics[:20]  # newest first slice
    chronological = list(reversed(recent))  # oldest→newest for chart x‑axis
    out = []
    for s in chronological:
        snap: ScrapingMetricsSnapshot = s["snapshot"]
        out.append({
            "date": s["datetime"].strftime("%m/%d %H:%M"),
            "shows": snap.shows.scraped,
            "saved": snap.shows.saved,
            "inserted": snap.shows.inserted,
            "updated": snap.shows.updated,
            "failed_saves": snap.shows.failed_save,
            "errors": snap.errors.total,
            "success_rate": float(snap.success_rate or 0.0),
        })
    return out


def build_error_details_rows(error_details_snapshot: List[Any]) -> str:
    if error_details_snapshot:
        rows = []
        for e in error_details_snapshot:
            rows.append(
                f"""
            <tr>
                <td>{(e.club or '')}</td>
                <td>{(e.error or '')}</td>
            </tr>
            """
            )
        return "".join(rows)
    return """
        <tr>
            <td colspan="2" style="text-align: center; color: green;">🎉 No scraping errors in latest session!</td>
        </tr>
        """


def build_db_operations_rows(latest: Dict[str, Any]) -> str:
    snap: ScrapingMetricsSnapshot = latest["snapshot"]
    latest_scraped = snap.shows.scraped
    latest_saved = snap.shows.saved
    latest_inserted = snap.shows.inserted
    latest_updated = snap.shows.updated
    latest_failed_saves = snap.shows.failed_save
    latest_skipped_dedup = snap.shows.skipped_dedup
    latest_validation_failed = snap.shows.validation_failed
    latest_db_errors = snap.shows.db_errors
    db_summary_class = "success" if latest_failed_saves == 0 else "error"
    db_summary_emoji = "✅" if latest_failed_saves == 0 else "❌"
    rows = f"""
                    <tr class="success">
                        <td>Shows Scraped</td>
                        <td>{latest_scraped:,}</td>
                        <td>✅ Complete</td>
                    </tr>
                    <tr class="{db_summary_class}">
                        <td>Shows Saved</td>
                        <td>{latest_saved:,}</td>
                        <td>{db_summary_emoji} {"Success" if latest_failed_saves == 0 else "With Failures"}</td>
                    </tr>
                    <tr class="success">
                        <td>New Shows Inserted</td>
                        <td>{latest_inserted:,}</td>
                        <td>✅ Complete</td>
                    </tr>
                    <tr class="success">
                        <td>Shows Updated</td>
                        <td>{latest_updated:,}</td>
                        <td>✅ Complete</td>
                    </tr>"""
    if latest_failed_saves > 0:
        rows += f"""
                    <tr class="error">
                        <td>Failed Saves</td>
                        <td>{latest_failed_saves:,}</td>
                        <td>❌ Failed</td>
                    </tr>"""
    if any([latest_skipped_dedup, latest_validation_failed, latest_db_errors]):
        if latest_skipped_dedup:
            rows += f"""
                    <tr>
                        <td>Skipped (Dedup)</td>
                        <td>{int(latest_skipped_dedup):,}</td>
                        <td>ℹ️ Deduplicated</td>
                    </tr>"""
        if latest_validation_failed:
            rows += f"""
                    <tr class="error">
                        <td>Validation Failures</td>
                        <td>{int(latest_validation_failed):,}</td>
                        <td>❌ Invalid Input</td>
                    </tr>"""
        if latest_db_errors:
            rows += f"""
                    <tr class="error">
                        <td>DB Errors (Batches)</td>
                        <td>{int(latest_db_errors):,}</td>
                        <td>❌ Database Errors</td>
                    </tr>"""
    return rows


def build_dedup_widget_html(latest: Dict[str, Any]) -> str:
    snap: ScrapingMetricsSnapshot = latest["snapshot"]
    duplicate_details = [asdict(d) for d in (snap.duplicate_show_details or [])]
    if not duplicate_details:
        return "<div class=\"dedup-card\" style=\"margin-top:12px;\"><div class=\"dedup-header\"><h3 class=\"dedup-title\">Deduped Shows (Latest)</h3><div class=\"muted\" style=\"padding:10px 16px;\">No deduplicated shows in the latest session.</div></div></div>"
    duplicates_data_json = json.dumps(duplicate_details)
    # Build HTML as raw template string with placeholder to avoid escaping braces in f-strings.
    html = r"""
        <style>
            /* Dedup table styling */
            .dedup-card {{
                margin-top: 16px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                overflow: hidden;
            }}
            .dedup-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                background: #f8fafc;
                border-bottom: 1px solid #eaecef;
            }}
            .dedup-title {{
                margin: 0;
                color: #0b75c9;
                font-size: 1.05rem;
                font-weight: 600;
            }}
            .dedup-controls {{
                display: flex;
                gap: 12px;
                align-items: center;
                flex-wrap: wrap;
            }}
            .dedup-title-wrap {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .dedup-badge {{
                display: none;
                padding: 4px 8px;
                border-radius: 999px;
                background: #eaf5ff;
                color: #0366d6;
                border: 1px solid #c8e1ff;
                font-size: 0.85rem;
                font-weight: 600;
                white-space: nowrap;
            }}
            .dedup-controls label {{
                color: #555;
                font-size: 0.9rem;
                margin-right: 4px;
            }}
            .dedup-controls select {{
                padding: 6px 8px;
                border-radius: 6px;
                border: 1px solid #d0d7de;
                background: #fff;
                font-size: 0.9rem;
            }}
            .dedup-table-wrapper {{
                max-height: 520px;
                overflow: auto;
            }}
            table.dedup-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.92em;
            }}
            table.dedup-table thead th {{
                position: sticky;
                top: 0;
                background: #f3f4f6;
                z-index: 1;
                border-bottom: 1px solid #e5e7eb;
            }}
            table.dedup-table th, table.dedup-table td {{
                padding: 10px 8px;
                border-bottom: 1px solid #eee;
                text-align: left;
            }}
            table.dedup-table tbody tr:hover {{
                background: #f9fafb;
            }}
            .text-right {{ text-align: right; }}
            .muted {{ color: #666; }}
            .dedup-pagination {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 16px;
                background: #fafafa;
                border-top: 1px solid #eaecef;
                font-size: 0.9rem;
            }}
            .dedup-pagination .buttons {{ display: flex; gap: 6px; }}
            .dedup-button {{
                padding: 6px 10px;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background: #fff;
                color: #24292f;
                cursor: pointer;
            }}
            .dedup-button:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
        </style>
        <div class="dedup-card" id="dedup-widget">
            <div class="dedup-header">
                <div class="dedup-title-wrap">
                    <h3 class="dedup-title">Deduped Shows (Latest)</h3>
                    <span class="dedup-badge" id="dedup-badge"></span>
                </div>
                <div class="dedup-controls">
                    <div>
                        <label for="dedup-page-size">Page size</label>
                        <select id="dedup-page-size">
                            <option value="10">10</option>
                            <option value="25" selected>25</option>
                            <option value="50">50</option>
                            <option value="100">100</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="dedup-table-wrapper">
                <table class="dedup-table" id="dedup-table">
                    <thead>
                        <tr>
                            <th>Club</th>
                            <th>Date</th>
                            <th>Room</th>
                            <th>Kept Name</th>
                            <th>Kept URL</th>
                            <th>Dropped Shows</th>
                            <th class="text-right">Dropped Count</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
            <div class="dedup-pagination">
                <div class="muted" id="dedup-page-info"></div>
                <div class="buttons">
                    <button class="dedup-button" id="dedup-prev">Prev</button>
                    <button class="dedup-button" id="dedup-next">Next</button>
                </div>
            </div>
        </div>
        <script>
    (function(){
            const data = __DUPLICATES_DATA__;
            // State now tracks selected club by numeric id (as string)
            const state = { page: 1, pageSize: 25, clubId: '', clubName: '' };
            const el = document.getElementById('dedup-widget');
            const tbody = el.querySelector('#dedup-table tbody');
            const pageSizeSelect = el.querySelector('#dedup-page-size');
            const pageInfo = el.querySelector('#dedup-page-info');
            const prevBtn = el.querySelector('#dedup-prev');
            const nextBtn = el.querySelector('#dedup-next');
            function filtered() {
                const selectedId = state.clubId;
                return (data||[]).filter(function(d){
                    if (!selectedId) return true;
                    const cid = (d && d.club_id != null) ? String(d.club_id) : '';
                    return cid === selectedId;
                });
            }
            function totalPages() {
                const n = filtered().length;
                return Math.max(1, Math.ceil(n / state.pageSize));
            }
            function sanitize(s) { return (s ?? '').toString(); }
            function render() {
                const list = filtered();
                if (state.page > totalPages()) state.page = totalPages();
                if (state.page < 1) state.page = 1;
                const start = (state.page - 1) * state.pageSize;
                const pageItems = list.slice(start, start + state.pageSize);
                tbody.innerHTML = pageItems.map(function(d) {
                    const clubName = (d && d.club_name) ? String(d.club_name) : '-';
                    const date = sanitize(d && d.date);
                    const room = sanitize(((d && d.room) || '').trim ? ((d.room)||'').trim() : ((d && d.room) || ''));
                    const keptName = sanitize(d && d.kept ? d.kept.name : '');
                    const keptUrl = (d && d.kept && d.kept.show_page_url) ? '<a href="' + d.kept.show_page_url + '" target="_blank">link</a>' : '';
                    const droppedCount = (d && d.dropped && d.dropped.length) ? d.dropped.length : 0;
                    const droppedList = (d && d.dropped && d.dropped.length) ? '<ul style="margin:0;padding-left:16px;">' + d.dropped.map(function(x){
                        const nm = sanitize(x && x.name);
                        const link = (x && x.show_page_url) ? ' <a href="'+x.show_page_url+'" target="_blank">link</a>' : '';
                        return '<li style="margin:0;">'+ nm + link + '</li>';
                    }).join('') + '</ul>' : '';
                    return '<tr>' +
                           '<td>' + clubName + '</td>' +
                           '<td>' + date + '</td>' +
                           '<td>' + room + '</td>' +
                           '<td>' + keptName + '</td>' +
                           '<td>' + keptUrl + '</td>' +
                           '<td>' + droppedList + '</td>' +
                           '<td class="text-right">' + droppedCount + '</td>' +
                           '</tr>';
                }).join('');
                pageInfo.textContent = 'Page ' + state.page + ' of ' + totalPages() + ' — ' + list.length + ' rows';
                prevBtn.disabled = state.page <= 1;
                nextBtn.disabled = state.page >= totalPages();
                const badge = el.querySelector('#dedup-badge');
                if (badge) {
                    if (state.clubId) {
                        const totalDedup = list.reduce(function(acc, d) {
                            const n = (d && d.dropped && d.dropped.length) ? d.dropped.length : 0;
                            return acc + n;
                        }, 0);
                        const label = state.clubName ? state.clubName + ' (#' + state.clubId + ')' : 'Club #' + state.clubId;
                        badge.textContent = label + ' deduped: ' + totalDedup;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.textContent = '';
                        badge.style.display = 'none';
                    }
                }
            }
            pageSizeSelect.addEventListener('change', () => { state.pageSize = parseInt(pageSizeSelect.value, 10) || 25; state.page = 1; render(); });
            prevBtn.addEventListener('click', () => { if (state.page > 1) { state.page--; render(); } });
            nextBtn.addEventListener('click', () => { if (state.page < totalPages()) { state.page++; render(); } });
            render();
            window.DEDUP_WIDGET = {
                // Primary API: setClubId
                setClubId: function(id) {
                    const cid = id ? String(id) : '';
                    state.clubId = cid;
                    if (!cid) {
                        state.clubName = '';
                    } else {
                        const match = (data||[]).find(d => String(d && d.club_id) === cid);
                        state.clubName = match && match.club_name ? String(match.club_name) : '';
                    }
                    state.page = 1;
                    render();
                },
                // Deprecated alias: setClubName (kept for backward compatibility)
                setClubName: function(id) {
                    if (typeof console !== 'undefined' && console.warn) {
                        console.warn('[DEDUP_WIDGET] setClubName is deprecated; use setClubId');
                    }
                    this.setClubId(id);
                },
                clear: function() { this.setClubId(''); }
            };
    })();
        </script>
    """
    return html.replace("__DUPLICATES_DATA__", duplicates_data_json)
