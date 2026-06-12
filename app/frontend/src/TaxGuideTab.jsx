export default function TaxGuideTab() {
  return (
    <div className="tax-guide">
      <h2>What changes when you move back to Israel</h2>
      <p>
        While you live abroad as a non-Israeli tax resident, only the country where the property
        sits taxes your rental income and gains. The moment you become an Israeli tax resident
        again (183-day or centre-of-life test), Israel taxes your <strong>worldwide</strong> income —
        including rent from Sofia, Sicily or Athens. The treaties with Bulgaria, Italy and Greece
        all give the property's country first taxing rights; Israel then taxes on top, under one
        of two tracks you choose each year:
      </p>

      <div className="tax-cards">
        <section className="card">
          <h3>Track 1 — 15% flat (Section 122A)</h3>
          <ul>
            <li>15% on <strong>gross</strong> foreign rent, minus depreciation only.</li>
            <li>No expense deductions.</li>
            <li><strong>No foreign tax credit</strong> — the 15% stacks on top of Bulgarian /
              Italian / Greek tax. Total burden ≈ local rate + 15%.</li>
            <li>Best when local tax is low (Bulgaria's effective 9%) and expenses are small.</li>
          </ul>
        </section>
        <section className="card">
          <h3>Track 2 — Marginal rate with credit</h3>
          <ul>
            <li>Rent added to your ordinary income: up to 47% (+3% surtax above ~₪722k).</li>
            <li>Taxed on <strong>net</strong> income after expenses and depreciation.</li>
            <li><strong>Foreign tax fully creditable</strong> — you pay only the excess of the
              Israeli bill over the local one.</li>
            <li>Best when local tax is already high (Greece's upper brackets) or your Israeli
              marginal rate is low.</li>
          </ul>
        </section>
        <section className="card">
          <h3>Returning-resident exemptions</h3>
          <ul>
            <li>⚠ <strong>Fewer than 6 consecutive years abroad: no exemption at all</strong> —
              you choose between the two tracks from the day residency resumes.</li>
            <li><strong>Ordinary toshav chozer</strong> (6+ yrs abroad): foreign passive income —
              including rent — from assets bought while abroad is <strong>exempt for 5 years</strong>;
              capital gains on those assets exempt for 10 years.</li>
            <li><strong>Toshav chozer vatik</strong> (10+ yrs abroad): <strong>all</strong> foreign
              income and gains exempt for <strong>10 years</strong>.</li>
            <li>⚠ Buy <em>before</em> you re-establish residency: the ordinary exemption covers only
              assets acquired while you were still non-resident.</li>
            <li>⚠ From 1 Jan 2026 the <strong>reporting</strong> exemption is cancelled — exempt
              income and foreign assets must still be declared from day one (Amendment 272).</li>
          </ul>
        </section>
      </div>

      <h2>Local taxes that always apply (treaty: situs country taxes first)</h2>
      <table className="compare">
        <thead>
          <tr><th></th><th>Sofia (Bulgaria)</th><th>Sicily (Italy)</th><th>Athens (Greece)</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Rental income</td>
            <td>10% flat after a 10% notional deduction (≈9% of gross)</td>
            <td>Cedolare secca: 21% flat on gross (26% from 2nd property)</td>
            <td>Progressive: 15% to €12k · 25% to €24k · 35% to €35k · 45% above</td>
          </tr>
          <tr>
            <td>Annual property tax</td>
            <td>~0.15–0.45% municipal</td>
            <td>IMU ≈ 0.4–1.06% of cadastral value (second homes)</td>
            <td>ENFIA €2–16.2/m² + municipal fee</td>
          </tr>
          <tr>
            <td>Capital gains</td>
            <td>10%</td>
            <td>26% — but <strong>0% after 5 years</strong> of ownership</td>
            <td>Suspended (0%) through 2026; 15% if reinstated</td>
          </tr>
        </tbody>
      </table>

      <h2>Short lets: an extra Israeli wrinkle</h2>
      <p>
        An actively-managed short-let operation (Airbnb-style) risks being classified by the ITA
        as <strong>business income</strong>, which would deny the 15% flat track and tax profits at
        marginal rates (with a foreign tax credit). Running it through a local management company
        strengthens the passive characterisation. Locally: Greece requires an AMA number (new
        registrations frozen in central Athens Districts 1–3 until end-2026), Italy requires a CIN
        code (21% first property, 26% second, business status from the third), Bulgaria requires
        municipal categorisation as tourist accommodation.
      </p>

      <h2>Capital gains when you sell, as an Israeli resident</h2>
      <p>
        Israel taxes the real (inflation-adjusted) gain at <strong>25%</strong> (+ surtax for high
        incomes), with a credit for foreign CGT paid. Practical consequences: in Italy a sale after
        year 5 is locally tax-free, so the full 25% Israeli tax applies; in Bulgaria you credit the
        10% and top up 15% to Israel; in Greece, while the local suspension holds, the full 25%
        goes to Israel. Veteran returning residents selling inside the 10-year window pay nothing;
        sales after the window are split linearly between exempt and taxable periods.
      </p>

      <p className="note">
        Sources: PwC Tax Summaries (Israel, Bulgaria, Italy, Greece), Israel Tax Authority guidance
        on Sec. 122A and returning residents, Amendment 272 (2026 disclosure rules). Figures as of
        June 2026. This is modelling, not tax advice — confirm with an Israeli CPA before acting.
      </p>
    </div>
  )
}
