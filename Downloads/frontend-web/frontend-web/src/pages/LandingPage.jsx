import { useEffect, useRef } from "react";
import "./LandingPage.css";

export default function LandingPage({ onGetStarted }) {
  const navRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => navRef.current?.classList.toggle("scrolled", window.scrollY > 20);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add("visible"); }),
      { threshold: 0.1 }
    );
    document.querySelectorAll(".anim").forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  const bars = [45, 72, 38, 90, 55, 28, 62];
  const dayLabels = ["M","T","W","T","F","S","S"];

  return (
    <div className="lp">
      {/* NAV */}
      <nav className="lp-nav" ref={navRef}>
        <div className="lp-logo">TYE<span>.</span></div>
        <ul className="lp-links">
          <li><a href="#features">Features</a></li>
          <li><a href="#how">How It Works</a></li>
          <li><a href="#reviews">Reviews</a></li>
        </ul>
        <div className="lp-nav-cta">
          <button className="btn-nav-ghost" onClick={onGetStarted}>Log In</button>
          <button className="btn-nav-solid" onClick={onGetStarted}>Get Started</button>
        </div>
      </nav>

      {/* HERO */}
      <section className="lp-hero">
        <div className="lp-hero-inner">
          <div className="lp-hero-content">
            <div className="lp-eyebrow"><span className="eyebrow-dot"></span>Smart Expense Intelligence</div>
            <h1>Your money.<br/><em>Finally</em><span className="h1-line2"> understood.</span></h1>
            <p className="lp-sub">TYE transforms how you see your spending. Beautiful dashboards, intelligent budgets, and real insights — all in one place.</p>
            <div className="lp-hero-btns">
              <button className="btn-hero-primary" onClick={onGetStarted}>Start for Free →</button>
              <a href="#how" className="btn-hero-ghost">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polygon points="10,8 16,12 10,16"/></svg>
                See How It Works
              </a>
            </div>
            <div className="lp-trust">
              <div className="trust-item"><span className="trust-dot"></span>No credit card</div>
              <div className="trust-item"><span className="trust-dot"></span>100% free</div>
              <div className="trust-item"><span className="trust-dot"></span>Your data stays private</div>
            </div>
          </div>

          {/* 3D CARD */}
          <div className="lp-scene">
            <div className="card3d">
              <div className="card3d-glow"></div>
              <div className="card3d-main">
                <div className="c3-header">
                  <span className="c3-dot" style={{background:"#FF5F57"}}></span>
                  <span className="c3-dot" style={{background:"#FEBC2E",marginLeft:5}}></span>
                  <span className="c3-dot" style={{background:"#28C840",marginLeft:5}}></span>
                  <span className="c3-title">TYE Dashboard</span>
                </div>
                <div className="c3-body">
                  <div className="c3-top">
                    <div>
                      <div className="c3-bal-lbl">Total Spent — March</div>
                      <div className="c3-bal">৳28,430</div>
                    </div>
                    <div className="c3-badge">↓ 12% vs last month</div>
                  </div>
                  <div className="c3-stats">
                    <div className="c3-stat"><div className="c3-stat-lbl">Budget</div><div className="c3-stat-val" style={{color:"var(--gold)"}}>৳45k</div></div>
                    <div className="c3-stat"><div className="c3-stat-lbl">Left</div><div className="c3-stat-val" style={{color:"var(--teal)"}}>৳16.6k</div></div>
                    <div className="c3-stat"><div className="c3-stat-lbl">Goals</div><div className="c3-stat-val" style={{color:"var(--violet)"}}>3 active</div></div>
                  </div>
                  <div className="c3-chart-area">
                    <div className="c3-chart-lbl">Weekly Spending</div>
                    <div className="c3-bars">
                      {bars.map((h, i) => (
                        <div key={i} className="c3-bar-wrap">
                          <div className="c3-bar" style={{height:`${h}%`,animationDelay:`${i*0.1}s`}}></div>
                          <span className="c3-bar-lbl">{dayLabels[i]}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="c3-txs">
                    {[["🍜","rgba(249,115,22,.15)","rgba(249,115,22,.3)","Lunch — Dhanmondi","৳320"],
                      ["🚌","rgba(59,130,246,.15)","rgba(59,130,246,.3)","Uber Ride","৳180"],
                      ["🛍️","rgba(168,85,247,.15)","rgba(168,85,247,.3)","Shopping","৳1,500"]].map(([ico,bg,border,name,amt]) => (
                      <div key={name} className="c3-tx">
                        <div className="c3-tx-ico" style={{background:bg,borderColor:border}}>{ico}</div>
                        <span className="c3-tx-name">{name}</span>
                        <span className="c3-tx-amt">{amt}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="float-badge b1"><span className="badge-dot" style={{background:"var(--green)"}}></span>Budget on track</div>
              <div className="float-badge b2">💰 ৳12k saved this month</div>
              <div className="float-badge b3">📈 Spending down 12%</div>
            </div>
          </div>
        </div>
      </section>

      {/* STATS BAND */}
      <div className="stats-band">
        <div className="stats-band-inner">
          {[["1k+","Active Users"],["৳2M+","Tracked Monthly"],["98%","Satisfaction Rate"],["Free","Forever"]].map(([n,l],i) => (
            <div key={l} className={`sband-item anim anim-d${i}`}>
              <div className="sband-num">{n}</div>
              <div className="sband-lbl">{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* FEATURES */}
      <section className="lp-features" id="features">
        <div className="lp-sec-inner">
          <div className="anim">
            <div className="sec-eyebrow">Features</div>
            <h2 className="sec-title">Built for people who want to<br/>actually <em>understand</em> money</h2>
          </div>
          <div className="feat-grid">
            {[
              ["📝","#e8b84b","01","Instant Expense Logging","Add any expense in under 5 seconds. Amount, category, description, date — minimal and fast.","Core Feature","rgba(232,184,75,.1)","var(--gold)","rgba(232,184,75,.2)"],
              ["📊","#7c6af7","02","Visual Analytics","Beautiful charts reveal your spending patterns instantly. Pie charts, bar graphs, monthly trends.","Insights","rgba(124,106,247,.1)","var(--violet)","rgba(124,106,247,.2)"],
              ["🎯","#2dd4bf","03","Smart Budget Alerts","Set monthly limits per category. Get warned before you overspend — not after.","Smart","rgba(45,212,191,.1)","var(--teal)","rgba(45,212,191,.2)"],
              ["💰","#4ade80","04","Savings Goal Tracker","Set targets for big purchases or your emergency fund. Visual progress bars keep you motivated.","Goals","rgba(74,222,128,.1)","var(--green)","rgba(74,222,128,.2)"],
              ["🏷️","#e8b84b","05","Custom Categories","Default categories plus full customization. Auto icon detection based on the name.","Flexible","rgba(232,184,75,.1)","var(--gold)","rgba(232,184,75,.2)"],
              ["🔐","#ff6b6b","06","Google Sign-In","One-click login. Your data is tied to your Google account — private and always accessible.","Secure","rgba(255,107,107,.1)","var(--red)","rgba(255,107,107,.2)"],
            ].map(([ico,icoBg,num,title,desc,tag,tagBg,tagColor,tagBorder],i) => (
              <div key={title} className={`feat-card anim${i>0?` anim-d${Math.min(i%3,3)}`:''}`}>
                <div className="feat-card-top">
                  <div className="feat-ico" style={{background:`${icoBg}22`,border:`1px solid ${icoBg}44`}}>{ico}</div>
                  <span className="feat-num">{num}</span>
                </div>
                <h3>{title}</h3>
                <p>{desc}</p>
                <span className="feat-tag" style={{background:tagBg,color:tagColor,border:`1px solid ${tagBorder}`}}>{tag}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW */}
      <section className="lp-how" id="how">
        <div className="lp-sec-inner">
          <div className="anim">
            <div className="sec-eyebrow">How It Works</div>
            <h2 className="sec-title">From signup to <em>clarity</em><br/>in 60 seconds</h2>
          </div>
          <div className="how-grid">
            <div className="how-steps">
              {[["01","Sign in with Google","One tap. No forms, no passwords. Your Google account creates your TYE profile instantly."],
                ["02","Log your first expense","Add the amount, pick a category, set a date. Takes less than 10 seconds. Keep going."],
                ["03","Set your budgets","Tell TYE how much you want to spend per category. Get alerted before limits are reached."],
                ["04","Watch your insights grow","The more you log, the smarter your dashboard gets. Monthly trends, category breakdowns, goal progress."]
              ].map(([n,t,d]) => (
                <div key={n} className="how-step">
                  <div className="how-step-num">{n}</div>
                  <div><h3>{t}</h3><p>{d}</p></div>
                </div>
              ))}
            </div>
            <div className="how-visual anim">
              <div className="how-screen">
                <div className="how-screen-hdr">
                  {["#FF5F57","#FEBC2E","#28C840"].map(c => <span key={c} style={{width:9,height:9,borderRadius:"50%",background:c,display:"inline-block",marginLeft:c=="#FF5F57"?0:5}}></span>)}
                  <span style={{marginLeft:"auto",marginRight:"auto",fontFamily:"var(--fm)",fontSize:".55rem",color:"var(--white3)"}}>Recent Transactions</span>
                </div>
                <div className="how-screen-body">
                  {[["🍜","rgba(249,115,22,.15)","Lunch — Bashundhara","2026-03-14","৳420"],
                    ["🚌","rgba(59,130,246,.15)","Uber to office","2026-03-13","৳250"],
                    ["🛍️","rgba(168,85,247,.15)","Clothing — Aarong","2026-03-12","৳2,800"],
                    ["⚡","rgba(232,184,75,.15)","Electricity Bill","2026-03-10","৳950"],
                    ["🎬","rgba(45,212,191,.15)","Netflix Subscription","2026-03-08","৳400"],
                  ].map(([ico,bg,name,date,amt]) => (
                    <div key={name} className="hs-row">
                      <div className="hs-ico" style={{background:bg}}>{ico}</div>
                      <div className="hs-info"><div className="hs-name">{name}</div><div className="hs-date">{date}</div></div>
                      <div className="hs-amt">{amt}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* REVIEWS */}
      <section className="lp-reviews" id="reviews">
        <div className="lp-sec-inner">
          <div className="anim">
            <div className="sec-eyebrow">Reviews</div>
            <h2 className="sec-title">People who took <em>control</em></h2>
          </div>
          <div className="reviews-grid">
            {[["R","var(--gold)","Rafi Ahmed","Freelance Designer, Dhaka","I never realized how much I was spending on food delivery until TYE showed me the monthly breakdown. Changed my habits completely."],
              ["N","var(--violet)","Nusrat Islam","Graduate Student, BUET","The budget alert system is exactly what I needed. I get warned before I overspend — not after the damage is done. Total game changer."],
              ["K","var(--teal)","Karim Hossain","Small Business Owner","Clean, fast, and actually useful. I've tried Mint, Wallet, and five other apps. TYE is the first one I've stuck with for more than a week."],
            ].map(([init,color,name,role,quote],i) => (
              <div key={name} className={`review-card anim${i>0?` anim-d${i}`:''}`}>
                <div className="review-quote">"</div>
                <div className="review-stars">★★★★★</div>
                <p>"{quote}"</p>
                <div className="review-author">
                  <div className="review-avatar" style={{background:color,color:"var(--bg)"}}>{init}</div>
                  <div><div className="review-name">{name}</div><div className="review-role">{role}</div></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="lp-cta">
        <div className="cta-glow"></div>
        <div className="lp-sec-inner" style={{textAlign:"center",position:"relative"}}>
          <div className="cta-badge">✦ Start Today</div>
          <h2 className="sec-title" style={{maxWidth:600,margin:"0 auto 1.25rem"}}>Stop guessing.<br/>Start <em>knowing</em>.</h2>
          <p style={{color:"var(--white3)",marginBottom:"2.5rem",fontWeight:300,fontSize:"1rem",lineHeight:1.75}}>Join thousands of people who finally understand where their money goes.</p>
          <button className="btn-hero-primary" style={{fontSize:"1rem",padding:"1.1rem 2.8rem"}} onClick={onGetStarted}>Open TYE Free →</button>
        </div>
      </section>

      <footer className="lp-footer">
        <div className="footer-logo">TYE<span>.</span></div>
        <p style={{fontSize:".72rem",color:"var(--white3)"}}>© 2026 TYE – Track Your Expenses. Made with care.</p>
        <div className="footer-links"><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Contact</a></div>
      </footer>
    </div>
  );
}
