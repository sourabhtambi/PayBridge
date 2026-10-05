import json
COLORS = {
 'bg':'#F4F6FA','surface':'#FFFFFF','surface-sunken':'#EAEFF6',
 'text':'#101C32','text-secondary':'#44506A','text-muted':'#566178',
 'primary':'#0B57B7','primary-hover':'#09448F','on-primary':'#FFFFFF',
 'link':'#0B57B7','border-strong':'#6B7689','divider':'#D3DAE6',
 'focus-ring':'#0B57B7','focus-ring-on-dark':'#FFD166',
 'nav-bg':'#0B2545','nav-text':'#FFFFFF','nav-text-muted':'#BFD0E6','nav-active-bg':'#1B4577',
 'dev-bg':'#1F2937','dev-text':'#F9FAFB',
 'neutral-bg':'#E6EBF3','neutral-text':'#2E3A52',
 'info-bg':'#E1EDFF','info-text':'#0A3F86',
 'success-bg':'#E3F5EA','success-text':'#0B6A33',
 'warn-bg':'#FFF3D1','warn-text':'#6F4A00',
 'danger-bg':'#FDECEC','danger-text':'#A1161B','danger-border':'#C0262B','danger-solid':'#B3201F',
 'disabled-bg':'#E1E5EC','disabled-text':'#566178','placeholder':'#5F6B80',
 'skeleton':'#DCE3EE','skeleton-hi':'#EEF2F8',
}
# (fg, bg, usage, required)  required: 4.5 text, 3 large/non-text
PAIRS = [
 ('text','bg','Body text on page',4.5),('text','surface','Body text on cards/tables',4.5),('text','surface-sunken','Body text on sunken panels',4.5),
 ('text-secondary','bg','Secondary text on page',4.5),('text-secondary','surface','Secondary text on cards',4.5),('text-secondary','surface-sunken','Secondary text on sunken',4.5),
 ('text-muted','bg','Muted text (captions, hints) on page',4.5),('text-muted','surface','Muted text on cards',4.5),('text-muted','surface-sunken','Muted text on sunken',4.5),
 ('placeholder','surface','Input placeholder',4.5),
 ('link','surface','Link text on cards',4.5),('link','bg','Link text on page',4.5),('link','surface-sunken','Link text on sunken',4.5),
 ('on-primary','primary','Primary button label',4.5),('on-primary','primary-hover','Primary button label (hover)',4.5),
 ('on-primary','danger-solid','Danger button label',4.5),
 ('nav-text','nav-bg','Nav and header text',4.5),('nav-text-muted','nav-bg','Nav secondary text/labels',4.5),('nav-text','nav-active-bg','Active nav item',4.5),('nav-text-muted','nav-active-bg','Muted text on active nav',4.5),
 ('dev-text','dev-bg','Dev bar text',4.5),
 ('neutral-text','neutral-bg','Badge CREATED / neutral',4.5),('info-text','info-bg','Badge SUBMITTED / info',4.5),
 ('success-text','success-bg','Badge COMPLETED / success',4.5),('warn-text','warn-bg','Badge warn (stuck, unmatched)',4.5),
 ('danger-text','danger-bg','Badge FAILED / error banner',4.5),
 ('danger-text','surface','Field error text on cards',4.5),('danger-text','bg','Field error text on page',4.5),
 ('success-text','surface','Success text on cards',4.5),
 ('disabled-text','disabled-bg','Disabled button label (exempt, still met)',4.5),
 ('border-strong','surface','Input / control boundary on card',3),('border-strong','bg','Input / control boundary on page',3),
 ('danger-border','danger-bg','Error banner boundary',3),('danger-border','surface','Invalid input boundary on card',3),
 ('focus-ring','surface','Focus ring on cards',3),('focus-ring','bg','Focus ring on page',3),('focus-ring','surface-sunken','Focus ring on sunken',3),
 ('focus-ring-on-dark','nav-bg','Focus ring in nav',3),('focus-ring-on-dark','dev-bg','Focus ring in dev bar',3),
 ('primary','surface','Primary button boundary on card',3),
]
def lum(h):
    h=h.lstrip('#'); r,g,b=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    f=lambda c: c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)
def ratio(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb); return (hi+0.05)/(lo+0.05)
rows=[]
for fg,bg,use,req in PAIRS:
    r=ratio(COLORS[fg],COLORS[bg]); rows.append((fg,bg,use,req,r,r>=req))
if __name__=='__main__':
    bad=[r for r in rows if not r[5]]
    for r in rows: print(f"{r[0]:20}{r[1]:16}{r[4]:.2f} need {r[3]} {'OK' if r[5] else 'FAIL'}")
    print('FAILS',len(bad))
