/* ── Global Interactive Floating Elements ── */
(function(){
  // Only run if we aren't in a tiny iframe or something, though it's fine.
  window.addEventListener('DOMContentLoaded', () => {
    
    // Create the background container
    const fc = document.createElement('div');
    fc.id = 'global-floating-bg';
    fc.style.cssText = 'position:fixed;inset:0;overflow:hidden;z-index:0;pointer-events:none;';
    document.body.appendChild(fc);

    const logoSVG = `<svg viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%">
      <circle cx="18" cy="18" r="16" stroke="url(#flg1)" stroke-width="2"/>
      <path d="M18 6 L30 24 L6 24 Z" fill="url(#flg2)" opacity=".85"/>
      <circle cx="18" cy="18" r="4" fill="#00f5d4"/>
      <defs>
        <linearGradient id="flg1" x1="0" y1="0" x2="36" y2="36">
          <stop offset="0%" stop-color="#00f5d4"/><stop offset="100%" stop-color="#7b2ff7"/>
        </linearGradient>
        <linearGradient id="flg2" x1="0" y1="0" x2="36" y2="36">
          <stop offset="0%" stop-color="#00f5d4" stop-opacity=".5"/>
          <stop offset="100%" stop-color="#7b2ff7" stop-opacity=".5"/>
        </linearGradient>
      </defs>
    </svg>`;

    const defs = [
      /* Logos */
      { html:logoSVG,   w:72, h:72, spd:0.40, op:.10 },
      { html:logoSVG,   w:58, h:58, spd:0.55, op:.12 },
      { html:logoSVG,   w:44, h:44, spd:0.70, op:.08 },
      { html:logoSVG,   w:32, h:32, spd:0.85, op:.06 },
      { html:logoSVG,   w:26, h:26, spd:0.60, op:.05 },
      /* RECON-X text */
      { html:'RECON-X', w:160,h:46, spd:0.45, op:.08, mono:true, grad:'135deg,#00f5d4,#7b2ff7' },
      { html:'RECON-X', w:138,h:36, spd:0.65, op:.06, mono:true, grad:'135deg,#7b2ff7,#00f5d4' },
      { html:'RECON-X', w:96, h:26, spd:0.80, op:.05, mono:true, grad:'135deg,#00f5d4,#f72f8a' },
      { html:'RECON-X', w:72, h:20, spd:0.70, op:.04, mono:true, grad:'135deg,#7b2ff7,#00f5d4' },
      /* S letters */
      { html:'S', w:64, h:70, spd:0.50, op:.08, mono:true, col:'#00f5d4' },
      { html:'S', w:40, h:46, spd:0.75, op:.05, mono:true, col:'#7b2ff7' },
      /* D letters */
      { html:'D', w:64, h:70, spd:0.45, op:.08, mono:true, col:'#7b2ff7' },
      { html:'D', w:40, h:46, spd:0.72, op:.05, mono:true, col:'#00f5d4' },
    ];

    let W = window.innerWidth;
    let H = window.innerHeight;

    window.addEventListener('resize', () => {
      W = window.innerWidth;
      H = window.innerHeight;
    });

    const floaters = defs.map(def => {
      const el = document.createElement('div');
      let style = `position:absolute;pointer-events:none;user-select:none;
        display:flex;align-items:center;justify-content:center;
        width:${def.w}px;height:${def.h}px;opacity:${def.op};
        transition:filter .2s;will-change:left,top;`;
      
      if (def.mono && def.grad) {
        const fs = def.w > 120 ? '1.4rem' : (def.w > 90 ? '1rem' : '0.75rem');
        style += `font-family:"JetBrains Mono",monospace;font-size:${fs};font-weight:700;
          background:linear-gradient(${def.grad});-webkit-background-clip:text;
          -webkit-text-fill-color:transparent;white-space:nowrap;`;
      } else if (def.mono && def.col) {
        const fs = def.h > 60 ? '3rem' : (def.h > 40 ? '2rem' : '1.2rem');
        style += `font-family:"JetBrains Mono",monospace;font-size:${fs};font-weight:700;
          color:${def.col};line-height:1;`;
      }
      
      el.style.cssText = style;
      el.innerHTML = def.html;
      fc.appendChild(el);

      const angle = Math.random() * Math.PI * 2;
      return {
        el,
        x: 20 + Math.random() * Math.max(1, W - def.w - 40),
        y: 20 + Math.random() * Math.max(1, H - def.h - 40),
        vx: Math.cos(angle) * def.spd,
        vy: Math.sin(angle) * def.spd,
        angle,
        angleVel: 0,
        spd: def.spd,
        w: def.w, h: def.h,
      };
    });

    /* Mouse / touch tracking */
    let mx = -9999, my = -9999;
    document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
    document.addEventListener('mouseleave', () => { mx = -9999; my = -9999; });
    document.addEventListener('touchmove', e => {
      mx = e.touches[0].clientX;
      my = e.touches[0].clientY;
    }, {passive:true});
    document.addEventListener('touchend', () => { mx = -9999; my = -9999; });

    /* Hover effect */
    floaters.forEach(f => {
      f.el.addEventListener('mouseenter', () => { 
        f.el.style.filter='brightness(3) drop-shadow(0 0 12px #00f5d4)'; 
        f.el.style.opacity = '0.5';
      });
      f.el.addEventListener('mouseleave', () => { 
        f.el.style.filter='none'; 
        f.el.style.opacity = defs[floaters.indexOf(f)].op;
      });
    });

    const REPEL = 180, FORCE = 4.5, FRICTION = 0.96, MARGIN = 10;

    function tick() {
      floaters.forEach(f => {
        /* Wander steering */
        f.angleVel += (Math.random() - 0.5) * 0.015;
        f.angleVel  = Math.max(-0.03, Math.min(0.03, f.angleVel));
        f.angle    += f.angleVel;

        const tx = Math.cos(f.angle) * f.spd;
        const ty = Math.sin(f.angle) * f.spd;
        f.vx += (tx - f.vx) * 0.05;
        f.vy += (ty - f.vy) * 0.05;

        /* Repulsion */
        const cx = f.x + f.w/2, cy = f.y + f.h/2;
        const dx = cx - mx, dy = cy - my;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < REPEL && dist > 0) {
          const strength = (REPEL - dist) / REPEL * FORCE;
          f.vx += (dx/dist) * strength;
          f.vy += (dy/dist) * strength;
        }

        /* Wall avoidance */
        if (f.x < MARGIN) f.vx += 0.1;
        if (f.y < MARGIN) f.vy += 0.1;
        if (f.x + f.w > W - MARGIN) f.vx -= 0.1;
        if (f.y + f.h > H - MARGIN) f.vy -= 0.1;

        /* Speed limit */
        const spd = Math.sqrt(f.vx*f.vx + f.vy*f.vy);
        const maxSpd = f.spd * 8;
        if (spd > maxSpd) { f.vx = f.vx/spd*maxSpd; f.vy = f.vy/spd*maxSpd; }

        /* Friction applies only if speeding due to repulsion */
        if (spd > f.spd * 2) {
          f.vx *= FRICTION;
          f.vy *= FRICTION;
        }

        f.x += f.vx;
        f.y += f.vy;

        /* Hard boundary */
        f.x = Math.max(-50, Math.min(W - f.w + 50, f.x));
        f.y = Math.max(-50, Math.min(H - f.h + 50, f.y));

        f.el.style.left = f.x + 'px';
        f.el.style.top  = f.y + 'px';
      });

      requestAnimationFrame(tick);
    }
    
    // Slight delay to allow DOM/layout to settle
    setTimeout(tick, 100);
  });
})();
