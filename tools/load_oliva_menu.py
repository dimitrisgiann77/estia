# -*- coding: utf-8 -*-
"""Loader μενού «Oliva A la carte Restaurant» -> Asterias Village Resort (Piato · P-075).

Idempotent: ξανατρέξιμο ΔΕΝ διπλασιάζει (get-or-create ανά outlet/κατηγορία/πιάτο).
Το outlet μένει DRAFT (published=False) → ο υπεύθυνος επιβεβαιώνει αλλεργιογόνα + δημοσιεύει.

ΧΡΗΣΗ:
  Παραγωγή (από PC με το prod DATABASE_URL):
      DATABASE_URL="postgresql://..." python tools/load_oliva_menu.py
  Τοπικό preview (demo.db χωρίς Asterias):
      DATABASE_URL="sqlite:///_oliva.db" python tools/load_oliva_menu.py --create-hotel
  Σημαίες: --rebuild (σβήνει & ξαναφτιάχνει το outlet)  --publish (άμεση δημοσίευση)
           --create-hotel (φτιάχνει το ξεν. αν λείπει — ΜΟΝΟ για test)  --hotel "όνομα"

⚠️ ΑΛΛΕΡΓΙΟΓΟΝΑ: το έγγραφο ΔΕΝ τα ανέφερε. Οι ετικέτες παρακάτω είναι DRAFT (προφανή) —
   ο chef/F&B ΠΡΕΠΕΙ να τα επαληθεύσει ΠΡΙΝ τη δημοσίευση (EU 1169/2011).
"""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root -> import app

import app as A
from piato import (Outlet, MenuCategory, MenuItem, Allergen, ItemAllergen, _tok)
db = A.db

OUTLET_NAME = 'Oliva A la carte Restaurant'
HOURS = ''   # συμπληρώνεται από την κονσόλα

# (τίτλος_en, τιμή, περιγραφή_en, [allergen codes DRAFT])
MENU = [
 ('Appetizers', '', [
    ('Tzatziki', 6.00, 'Accompanied with mini rusks', ['milk', 'gluten']),
    ('Ntolmadakia', 7.00, 'Cretan grape leaves stuffed with rice', []),
    ('Dakos', 6.50, 'Cretan rusk with olive oil, tomato and crumbled feta cheese', ['gluten', 'milk']),
    ('Flutes', 6.00, 'Cured ham, kasseri cheese and sweet chili dip', ['gluten', 'milk']),
    ('Fried Squid', 7.00, 'Accompanied with a splash of tzatziki', ['molluscs', 'gluten', 'milk']),
    ('Mussels & Shrimps Saganaki', 9.50, 'Mussels, shrimps, vegetables, tomato sauce, garlic and ouzo', ['molluscs', 'crustaceans']),
    ('Stuffed Potato', 6.00, 'With selected vegetables & chilly sauce', []),
    ('French Fries', 5.00, '', []),
 ]),
 ('Salads', '', [
    ('Mixed Green Salad', 6.00, "Green leaves, mature balsamic vinaigrette", ['sulphites']),
    ('Greek Salad', 7.20, 'Tomatoes, cucumber, onions, green peppers, olives and feta', ['milk']),
    ('Cretan Salad', 8.50, 'Cherry tomatoes, cucumber, onions, green peppers, olives, eggs, potatoes, rusk', ['gluten', 'eggs']),
 ]),
 ('Main Courses', '', [
    ('Skioufichta', 8.90, 'Cretan fresh pasta with tomato sauce and vegetables', ['gluten']),
    ('Cretan Ravioli', 10.50, '', ['gluten', 'milk']),
    ('Braised Beef', 15.50, 'With mashed potatoes', ['milk']),
    ('Grilled Chicken Fillet', 13.50, 'With grilled vegetables and balsamic vinegar cream', ['sulphites']),
    ('Pork Chop', 13.50, 'With fried potatoes and pepper sauce', ['milk']),
    ('Chicken Souvlaki', 12.50, '', []),
    ('Pork Souvlaki', 12.50, '', []),
    ('Grilled Perch', 12.80, '', ['fish']),
    ('Sea Bream', 20.00, '', ['fish']),
    ('Mix Grill', 35.50, 'For 2', []),
    ('Lamb Chops', 27.00, '', []),
    ('Grilled Burgers', 14.50, 'With mashed potatoes', ['gluten', 'milk']),
    ('Pork Belly', 13.50, 'With BBQ sauce', []),
    ('Spaghetti Bolognese', 10.00, 'With minced meat of pork and beef', ['gluten']),
    ('Stable Pork Steak (800-900gr)', 25.00, '', []),
 ]),
 ('Desserts', '', [
    ('Chocolate Fudge', 6.00, '', ['gluten', 'milk', 'eggs']),
    ('Ice Cream', 4.00, '2 scoops of your choice: vanilla, chocolate and strawberry', ['milk']),
 ]),
]


def _i18n(en):
    return json.dumps({'en': en}, ensure_ascii=False) if en else '{}'


def _sq(s):
    """Escape single quote για ασφαλές SQL literal."""
    return (s or '').replace("'", "''")


def emit_sql(hotel_like='asterias'):
    """Παράγει Postgres DO-block (paste στο Railway Query console). Idempotent, DRAFT.
    ΠΡΟΫΠΟΘΕΣΗ: έχει γίνει push+deploy το Piato (τα piato_* + 14 αλλεργιογόνα υπάρχουν)."""
    L = []
    L.append('-- Piato · Oliva A la carte Restaurant -> Asterias Village Resort (P-075)')
    L.append('-- Paste ΟΛΟΚΛΗΡΟ στο Railway → Postgres → Query. Τρέξε ΜΕΤΑ το deploy του Piato.')
    L.append('-- Idempotent (αν υπάρχει ήδη το outlet → καμία αλλαγή). Το μενού μπαίνει DRAFT.')
    L.append('DO $$')
    L.append('DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;')
    L.append('BEGIN')
    L.append("  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%%%s%%' ORDER BY id LIMIT 1;" % _sq(hotel_like))
    L.append("  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Δεν βρέθηκε ξενοδοχείο (%%)', '%s'; END IF;" % _sq(hotel_like))
    L.append("  IF EXISTS (SELECT 1 FROM piato_outlet WHERE hotel_id=v_hotel AND name='%s') THEN" % _sq(OUTLET_NAME))
    L.append("     RAISE NOTICE 'Το outlet υπάρχει ήδη — καμία αλλαγή'; RETURN; END IF;")
    L.append("  INSERT INTO piato_outlet (hotel_id,name,otype,hours,qr_token,preview_token,published,sort,created_at,updated_at)")
    L.append("  VALUES (v_hotel,'%s','restaurant','',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,0,now(),now())" % _sq(OUTLET_NAME))
    L.append("  RETURNING id INTO v_outlet;")
    for ci, (cat_en, chours, items) in enumerate(MENU, start=1):
        L.append("  -- %s" % cat_en)
        L.append("  INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at)")
        L.append("  VALUES (v_outlet,'%s','',true,%d,now(),now()) RETURNING id INTO v_cat;" % (_sq(_i18n(cat_en)), ci))
        for ii, (t_en, price, desc_en, acodes) in enumerate(items, start=1):
            L.append("  INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at)")
            L.append("  VALUES (v_cat,'%s','%s',%.2f,'',true,%d,now(),now()) RETURNING id INTO v_item;"
                     % (_sq(_i18n(t_en)), _sq(_i18n(desc_en)), price, ii))
            if acodes:
                codes = ",".join("'%s'" % c for c in acodes)
                L.append("  INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN (%s);" % codes)
    L.append("  RAISE NOTICE 'OK: Oliva φορτώθηκε (DRAFT). Έλεγξε αλλεργιογόνα & δημοσίευσε από την κονσόλα.';")
    L.append('END $$;')
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hotel', default='asterias')
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--create-hotel', action='store_true')
    ap.add_argument('--emit-sql', action='store_true', help='τύπωσε SQL (paste στο Railway), χωρίς εγγραφή')
    args = ap.parse_args()

    if args.emit_sql:
        print(emit_sql(args.hotel))
        return 0

    with A.app.app_context():
        # 1) ξενοδοχείο
        h = A.Hotel.query.filter(A.Hotel.name.ilike('%%%s%%' % args.hotel)).first()
        if not h:
            if args.create_hotel:
                h = A.Hotel(name='Asterias Village Resort', is_active=True)
                db.session.add(h); db.session.commit()
                print('… δημιουργήθηκε ξενοδοχείο (test): %s (id=%d)' % (h.name, h.id))
            else:
                print('ΣΦΑΛΜΑ: δεν βρέθηκε ξενοδοχείο που να ταιριάζει «%s».' % args.hotel)
                print('Διαθέσιμα:')
                for x in A.Hotel.query.order_by(A.Hotel.id).all():
                    print('  - id=%d  %s  (active=%s)' % (x.id, x.name, x.is_active))
                print('Τρέξε ξανά με --hotel "<σωστό όνομα>" (ή --create-hotel για τοπικό test).')
                return 2

        # 2) outlet (get-or-create)
        allg = {a.code: a for a in Allergen.query.all()}
        if not allg:
            print('ΣΦΑΛΜΑ: δεν υπάρχουν αλλεργιογόνα (τρέξε την app μία φορά για seed).'); return 2
        o = Outlet.query.filter_by(hotel_id=h.id, name=OUTLET_NAME).first()
        if o and args.rebuild:
            db.session.delete(o); db.session.commit(); o = None
            print('… --rebuild: σβήστηκε το προηγούμενο outlet')
        if not o:
            o = Outlet(hotel_id=h.id, name=OUTLET_NAME, otype='restaurant', hours=HOURS,
                       qr_token=_tok(), preview_token=_tok(), published=False)
            db.session.add(o); db.session.commit()
            print('… δημιουργήθηκε outlet: %s' % OUTLET_NAME)
        else:
            print('… υπάρχον outlet (get-or-create): %s' % OUTLET_NAME)

        # 3) κατηγορίες + πιάτα (idempotent)
        n_cat = n_item = n_skip = 0
        for ci, (cat_en, chours, items) in enumerate(MENU, start=1):
            c = None
            for ex in o.categories:
                if json.loads(ex.name_i18n or '{}').get('en') == cat_en:
                    c = ex; break
            if not c:
                c = MenuCategory(outlet_id=o.id, name_i18n=_i18n(cat_en), hours=chours, sort=ci)
                db.session.add(c); db.session.commit(); n_cat += 1
            for ii, (t_en, price, desc_en, acodes) in enumerate(items, start=1):
                exists = any(json.loads(x.title_i18n or '{}').get('en') == t_en for x in c.items)
                if exists:
                    n_skip += 1; continue
                it = MenuItem(category_id=c.id, title_i18n=_i18n(t_en), desc_i18n=_i18n(desc_en),
                              price=price, available=True, sort=ii)
                db.session.add(it); db.session.flush()
                for code in acodes:
                    if code in allg:
                        db.session.add(ItemAllergen(item_id=it.id, allergen_id=allg[code].id))
                n_item += 1
            db.session.commit()

        if args.publish:
            o.published = True; db.session.commit()

        base = os.environ.get('PIATO_BASE_URL', 'https://estia.condianhotels.gr')
        print('\n' + '=' * 60)
        print('ΟΚ — Oliva -> %s' % h.name)
        print('  Κατηγορίες νέες: %d · Πιάτα νέα: %d · Παραλείφθηκαν (υπήρχαν): %d' % (n_cat, n_item, n_skip))
        print('  Κατάσταση: %s' % ('ΔΗΜΟΣΙΕΥΜΕΝΟ' if o.published else 'DRAFT (δεν φαίνεται στο κοινό)'))
        print('  Preview (μυστικό): %s/piato/preview/%s' % (base, o.preview_token))
        print('  Δημόσιο QR:        %s/piato/%s' % (base, o.qr_token))
        print('=' * 60)
        print('⚠️  ΑΛΛΕΡΓΙΟΓΟΝΑ = DRAFT (προφανή). Ο chef/F&B ΠΡΕΠΕΙ να τα επαληθεύσει')
        print('    στην κονσόλα (/dashboard/piato) ΠΡΙΝ τη δημοσίευση — EU 1169/2011.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
