def generate_alerts(gsc, ga4):
    alerts = []
    s  = gsc.get('summary', {})
    ps = gsc.get('prev_summary', {})
    gs = ga4.get('summary', {})
    gp = ga4.get('prev_summary', {})

    # Clicks dropped
    cur_clicks  = s.get('total_clicks', 0)
    prev_clicks = ps.get('total_clicks', 0)
    if prev_clicks > 0:
        chg = (cur_clicks - prev_clicks) / prev_clicks * 100
        if chg <= -20:
            alerts.append({'level':'critical','icon':'trending-down',
                'msg': f'Clicks dropped {abs(chg):.0f}% vs previous period ({prev_clicks} → {cur_clicks})'})
        elif chg <= -10:
            alerts.append({'level':'warning','icon':'trending-down',
                'msg': f'Clicks down {abs(chg):.0f}% vs previous period'})

    # Impressions dropped
    cur_imp  = s.get('total_impressions', 0)
    prev_imp = ps.get('total_impressions', 0)
    if prev_imp > 0:
        chg = (cur_imp - prev_imp) / prev_imp * 100
        if chg <= -15:
            alerts.append({'level':'warning','icon':'eye-off',
                'msg': f'Impressions down {abs(chg):.0f}% — Google showing your site less'})

    # Organic traffic critical
    org = gs.get('organic_sessions', 0)
    if org < 50:
        alerts.append({'level':'critical','icon':'alert-triangle',
            'msg': f'Organic traffic critically low: {org} sessions. Site needs urgent SEO work.'})
    elif org < 100:
        alerts.append({'level':'warning','icon':'alert-circle',
            'msg': f'Organic traffic still low: {org} sessions. Target is 500+/month.'})

    # Organic sessions dropped
    prev_org = gp.get('organic_sessions', 0)
    if prev_org > 0 and org < prev_org:
        chg = (org - prev_org) / prev_org * 100
        if chg <= -20:
            alerts.append({'level':'critical','icon':'trending-down',
                'msg': f'Organic traffic dropped {abs(chg):.0f}% vs previous period'})

    # Average position worsened
    cur_pos  = s.get('avg_position', 0)
    prev_pos = ps.get('avg_position', 0)
    if prev_pos > 0 and cur_pos > prev_pos + 2:
        alerts.append({'level':'warning','icon':'arrow-down',
            'msg': f'Average position worsened: {prev_pos} → {cur_pos} (higher = worse)'})

    # Low CTR keywords
    queries = gsc.get('queries', [])
    low_ctr = [r for r in queries if r.get('impressions',0) > 100 and r.get('ctr',0) < 0.01]
    if len(low_ctr) > 10:
        alerts.append({'level':'warning','icon':'mouse-pointer-click',
            'msg': f'{len(low_ctr)} keywords have >100 impressions but CTR below 1% — fix meta titles'})

    # Dying keywords (position > 50)
    dying = [r for r in queries if r.get('position',0) > 50]
    if len(dying) > 20:
        alerts.append({'level':'warning','icon':'skull',
            'msg': f'{len(dying)} keywords have dropped below position 50 — need content work'})

    # Positive alerts
    if prev_clicks > 0 and cur_clicks > prev_clicks * 1.1:
        alerts.append({'level':'good','icon':'trending-up',
            'msg': f'Clicks up {((cur_clicks-prev_clicks)/prev_clicks*100):.0f}% vs previous period'})

    top10 = s.get('keywords_top10', 0)
    if top10 >= 8:
        alerts.append({'level':'good','icon':'award',
            'msg': f'{top10} keywords ranking in Top 10 — good progress!'})

    if not alerts:
        alerts.append({'level':'good','icon':'check-circle',
            'msg': 'No critical issues detected. Keep up the SEO work!'})

    return alerts
