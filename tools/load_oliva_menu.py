# -*- coding: utf-8 -*-
"""Loader μενού «Oliva A la carte Restaurant» -> Asterias Village Resort (Piato · P-075).

ΔΙΓΛΩΣΣΟ (EL + EN): τίτλοι κατηγοριών/πιάτων + περιγραφή ανά γλώσσα.
Πηγή τιμών/EN: «AST - OLIVA MENU S26.docx» (03_REFERENCE/ΜΕΝΟΥ) — ΜΟΝΟ αγγλικά.
Τα Ελληνικά (τίτλοι+περιγραφές) είναι ΜΕΤΑΦΡΑΣΗ Cowork — ο F&B να τα ΕΠΑΛΗΘΕΥΣΕΙ πριν τη δημοσίευση.

Idempotent SYNC: ξανατρέξιμο ΔΕΝ διπλασιάζει και ΕΝΗΜΕΡΩΝΕΙ i18n (προσθέτει Ελληνικά σε υπάρχοντα
πιάτα/κατηγορίες), χωρίς να πειράζει allergens/published/qr tokens.

ΧΡΗΣΗ:
  Παραγωγή (PC με prod DATABASE_URL):  DATABASE_URL="postgresql://..." python tools/load_oliva_menu.py
  Τοπικό test (fresh sqlite):          DATABASE_URL="sqlite:///_oliva.db" python tools/load_oliva_menu.py --create-hotel
  Railway SQL (paste στο Query):       python tools/load_oliva_menu.py --emit-sql
  Σημαίες: --rebuild  --publish  --create-hotel(test)  --hotel "όνομα"

⚠️ ΑΛΛΕΡΓΙΟΓΟΝΑ: το έγγραφο ΔΕΝ τα ανέφερε — DRAFT (προφανή). Επαλήθευση chef/F&B (EU 1169/2011).
"""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root -> import app

import app as A
from piato import (Outlet, MenuCategory, MenuItem, Allergen, ItemAllergen, _tok)
db = A.db

OUTLET_NAME = 'Oliva A la carte Restaurant'
HOURS = ''   # συμπληρώνεται από την κονσόλα

# Κατηγορία: (name_en, name_el, hours, items)
# Πιάτο:     (title_en, title_el, price, desc_en, desc_el, [allergen codes DRAFT])
MENU = [
 ('Appetizers', 'Ορεκτικά', '', [
    ('Tzatziki', 'Τζατζίκι', 6.00, 'Accompanied with mini rusks', 'Συνοδεύεται με παξιμαδάκια', ['milk', 'gluten']),
    ('Ntolmadakia', 'Ντολμαδάκια', 7.00, 'Cretan grape leaves stuffed with rice', 'Κρητικά αμπελόφυλλα γεμιστά με ρύζι', []),
    ('Dakos', 'Ντάκος', 6.50, 'Cretan rusk with olive oil, tomato and crumbled feta cheese', 'Κρητικό παξιμάδι με ελαιόλαδο, ντομάτα και θρυμματισμένη φέτα', ['gluten', 'milk']),
    ('Flutes', 'Φλογέρες', 6.00, 'Cured ham, kasseri cheese and sweet chili dip', 'Ζαμπόν, κασέρι και ντιπ γλυκού τσίλι', ['gluten', 'milk']),
    ('Fried Squid', 'Καλαμαράκια τηγανητά', 7.00, 'Accompanied with a splash of tzatziki', 'Συνοδεύονται με λίγο τζατζίκι', ['molluscs', 'gluten', 'milk']),
    ('Mussels & Shrimps Saganaki', 'Μύδια & Γαρίδες σαγανάκι', 9.50, 'Mussels, shrimps, vegetables, tomato sauce, garlic and ouzo', 'Μύδια, γαρίδες, λαχανικά, σάλτσα ντομάτας, σκόρδο και ούζο', ['molluscs', 'crustaceans']),
    ('Stuffed Potato', 'Πατάτα γεμιστή', 6.00, 'With selected vegetables & chilly sauce', 'Με επιλεγμένα λαχανικά & σάλτσα τσίλι', []),
    ('French Fries', 'Πατάτες τηγανητές', 5.00, '', '', []),
 ]),
 ('Salads', 'Σαλάτες', '', [
    ('Mixed Green Salad', 'Πράσινη σαλάτα', 6.00, 'Green leaves, mature balsamic vinaigrette', 'Πράσινα φύλλα, βινεγκρέτ ώριμου βαλσάμικου', ['sulphites']),
    ('Greek Salad', 'Χωριάτικη σαλάτα', 7.20, 'Tomatoes, cucumber, onions, green peppers, olives and feta', 'Ντομάτα, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές και φέτα', ['milk']),
    ('Cretan Salad', 'Κρητική σαλάτα', 8.50, 'Cherry tomatoes, cucumber, onions, green peppers, olives, eggs, potatoes, rusk', 'Ντοματίνια, αγγούρι, κρεμμύδι, πράσινη πιπεριά, ελιές, αυγό, πατάτα, παξιμάδι', ['gluten', 'eggs']),
 ]),
 ('Main Courses', 'Κυρίως Πιάτα', '', [
    ('Skioufichta', 'Σκιουφιχτά', 8.90, 'Cretan fresh pasta with tomato sauce and vegetables', 'Κρητικά χειροποίητα ζυμαρικά με σάλτσα ντομάτας και λαχανικά', ['gluten']),
    ('Cretan Ravioli', 'Κρητικά ραβιόλια', 10.50, '', '', ['gluten', 'milk']),
    ('Braised Beef', 'Μοσχάρι κοκκινιστό', 15.50, 'With mashed potatoes', 'Με πουρέ πατάτας', ['milk']),
    ('Grilled Chicken Fillet', 'Φιλέτο κοτόπουλο σχάρας', 13.50, 'With grilled vegetables and balsamic vinegar cream', 'Με λαχανικά σχάρας και κρέμα βαλσάμικου', ['sulphites']),
    ('Pork Chop', 'Χοιρινή μπριζόλα', 13.50, 'With fried potatoes and pepper sauce', 'Με τηγανητές πατάτες και σάλτσα πιπεριού', ['milk']),
    ('Chicken Souvlaki', 'Κοτόπουλο σουβλάκι', 12.50, '', '', []),
    ('Pork Souvlaki', 'Χοιρινό σουβλάκι', 12.50, '', '', []),
    ('Grilled Perch', 'Πέρκα σχάρας', 12.80, '', '', ['fish']),
    ('Sea Bream', 'Τσιπούρα', 20.00, '', '', ['fish']),
    ('Mix Grill', 'Μιξ γκριλ', 35.50, 'For 2', 'Για 2 άτομα', []),
    ('Lamb Chops', 'Αρνίσια παϊδάκια', 27.00, '', '', []),
    ('Grilled Burgers', 'Μπιφτέκια σχάρας', 14.50, 'With mashed potatoes', 'Με πουρέ πατάτας', ['gluten', 'milk']),
    ('Pork Belly', 'Χοιρινή πανσέτα', 13.50, 'With BBQ sauce', 'Με σάλτσα BBQ', []),
    ('Spaghetti Bolognese', 'Σπαγγέτι μπολονέζ', 10.00, 'With minced meat of pork and beef', 'Με κιμά χοιρινό και μοσχαρίσιο', ['gluten']),
    ('Stable Pork Steak (800-900gr)', 'Χοιρινή μπριζόλα (800-900γρ.)', 25.00, '', '', []),
 ]),
 ('Desserts', 'Επιδόρπια', '', [
    ('Chocolate Fudge', 'Σοκολατόπιτα', 6.00, '', '', ['gluten', 'milk', 'eggs']),
    ('Ice Cream', 'Παγωτό', 4.00, '2 scoops of your choice: vanilla, chocolate and strawberry', '2 μπάλες της επιλογής σας: βανίλια, σοκολάτα, φράουλα', ['milk']),
 ]),
]


def _i18n(en, el=''):
    d = {}
    if el:
        d['el'] = el
    if en:
        d['en'] = en
    return json.dumps(d, ensure_ascii=False)


def _sq(s):
    return (s or '').replace("'", "''")


def emit_sql(hotel_like='asterias'):
    """Postgres DO-block, ΔΙΓΛΩΣΣΟ idempotent UPSERT (get-or-create + ενημέρωση i18n)."""
    L = []
    L.append('-- Piato · Oliva (EL+EN) -> Asterias Village Resort (P-075). Paste ΟΛΟΚΛΗΡΟ στο Railway Query.')
    L.append('-- Idempotent UPSERT: εισάγει νέα, ΕΝΗΜΕΡΩΝΕΙ τίτλους/περιγραφές σε υπάρχοντα. Μπαίνει DRAFT.')
    L.append('DO $$')
    L.append('DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;')
    L.append('BEGIN')
    L.append("  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%%%s%%' ORDER BY id LIMIT 1;" % _sq(hotel_like))
    L.append("  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Δεν βρέθηκε ξενοδοχείο'; END IF;")
    L.append("  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name='%s' LIMIT 1;" % _sq(OUTLET_NAME))
    L.append("  IF v_outlet IS NULL THEN")
    L.append("    INSERT INTO piato_outlet (hotel_id,name,otype,hours,layout,qr_token,preview_token,published,sort,created_at,updated_at)")
    L.append("    VALUES (v_hotel,'%s','restaurant','','spread',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,0,now(),now()) RETURNING id INTO v_outlet;" % _sq(OUTLET_NAME))
    L.append("  ELSE UPDATE piato_outlet SET layout='spread' WHERE id=v_outlet;")
    L.append("  END IF;")
    for ci, (cat_en, cat_el, chours, items) in enumerate(MENU, start=1):
        cj = _sq(_i18n(cat_en, cat_el))
        L.append("  -- %s / %s" % (cat_en, cat_el))
        L.append("  SELECT id INTO v_cat FROM piato_category WHERE outlet_id=v_outlet AND (name_i18n::jsonb->>'en')='%s' LIMIT 1;" % _sq(cat_en))
        L.append("  IF v_cat IS NULL THEN")
        L.append("    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'%s','',true,%d,now(),now()) RETURNING id INTO v_cat;" % (cj, ci))
        L.append("  ELSE UPDATE piato_category SET name_i18n='%s' WHERE id=v_cat; END IF;" % cj)
        for ii, (t_en, t_el, price, desc_en, desc_el, acodes) in enumerate(items, start=1):
            tj = _sq(_i18n(t_en, t_el))
            dj = _sq(_i18n(desc_en, desc_el))
            L.append("  SELECT id INTO v_item FROM piato_item WHERE category_id=v_cat AND (title_i18n::jsonb->>'en')='%s' LIMIT 1;" % _sq(t_en))
            L.append("  IF v_item IS NULL THEN")
            L.append("    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'%s','%s',%.2f,'',true,%d,now(),now()) RETURNING id INTO v_item;" % (tj, dj, price, ii))
            if acodes:
                codes = ",".join("'%s'" % c for c in acodes)
                L.append("    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN (%s);" % codes)
            L.append("  ELSE UPDATE piato_item SET title_i18n='%s', desc_i18n='%s' WHERE id=v_item; END IF;" % (tj, dj))
    L.append("  RAISE NOTICE 'OK: Oliva (EL+EN) φορτώθηκε/ενημερώθηκε (DRAFT).';")
    L.append('END $$;')
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hotel', default='asterias')
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--create-hotel', action='store_true')
    ap.add_argument('--emit-sql', action='store_true')
    args = ap.parse_args()

    if args.emit_sql:
        print(emit_sql(args.hotel))
        return 0

    with A.app.app_context():
        h = A.Hotel.query.filter(A.Hotel.name.ilike('%%%s%%' % args.hotel)).first()
        if not h:
            if args.create_hotel:
                h = A.Hotel(name='Asterias Village Resort', is_active=True)
                db.session.add(h); db.session.commit()
                print('… hotel(test):', h.name, h.id)
            else:
                print('ΣΦΑΛΜΑ: δεν βρέθηκε ξενοδοχείο «%s».' % args.hotel)
                for x in A.Hotel.query.order_by(A.Hotel.id).all():
                    print('  - id=%d  %s  (active=%s)' % (x.id, x.name, x.is_active))
                return 2

        allg = {a.code: a for a in Allergen.query.all()}
        if not allg:
            print('ΣΦΑΛΜΑ: δεν υπάρχουν αλλεργιογόνα (τρέξε την app για seed).'); return 2
        o = Outlet.query.filter_by(hotel_id=h.id, name=OUTLET_NAME).first()
        if o and args.rebuild:
            db.session.delete(o); db.session.commit(); o = None
            print('… --rebuild: σβήστηκε το προηγούμενο outlet')
        if not o:
            o = Outlet(hotel_id=h.id, name=OUTLET_NAME, otype='restaurant', hours=HOURS,
                       layout='spread', qr_token=_tok(), preview_token=_tok(), published=False)
            db.session.add(o); db.session.commit()
            print('… δημιουργήθηκε outlet: %s' % OUTLET_NAME)
        else:
            o.layout = 'spread'   # Δίστηλο (row-major) — προτίμηση Giannis
            print('… υπάρχον outlet (sync): %s' % OUTLET_NAME)

        n_cat = n_item = n_upd = 0
        for ci, (cat_en, cat_el, chours, items) in enumerate(MENU, start=1):
            c = None
            for ex in o.categories:
                if json.loads(ex.name_i18n or '{}').get('en') == cat_en:
                    c = ex; break
            if not c:
                c = MenuCategory(outlet_id=o.id, name_i18n=_i18n(cat_en, cat_el), hours=chours, sort=ci)
                db.session.add(c); db.session.commit(); n_cat += 1
            else:
                c.name_i18n = _i18n(cat_en, cat_el)   # sync: προσθήκη/ενημέρωση Ελληνικών
            for ii, (t_en, t_el, price, desc_en, desc_el, acodes) in enumerate(items, start=1):
                it = None
                for x in c.items:
                    if json.loads(x.title_i18n or '{}').get('en') == t_en:
                        it = x; break
                if not it:
                    it = MenuItem(category_id=c.id, title_i18n=_i18n(t_en, t_el),
                                  desc_i18n=_i18n(desc_en, desc_el), price=price, available=True, sort=ii)
                    db.session.add(it); db.session.flush()
                    for code in acodes:
                        if code in allg:
                            db.session.add(ItemAllergen(item_id=it.id, allergen_id=allg[code].id))
                    n_item += 1
                else:
                    it.title_i18n = _i18n(t_en, t_el)   # sync i18n
                    it.desc_i18n = _i18n(desc_en, desc_el)
                    n_upd += 1
            db.session.commit()

        if args.publish:
            o.published = True; db.session.commit()

        base = os.environ.get('PIATO_BASE_URL', 'https://estia.condianhotels.gr')
        print('\n' + '=' * 60)
        print('ΟΚ — Oliva (EL+EN) -> %s' % h.name)
        print('  Κατηγορίες νέες: %d · Πιάτα νέα: %d · Ενημερώθηκαν (i18n): %d' % (n_cat, n_item, n_upd))
        print('  Κατάσταση: %s' % ('ΔΗΜΟΣΙΕΥΜΕΝΟ' if o.published else 'DRAFT (δεν φαίνεται στο κοινό)'))
        print('  Preview (μυστικό): %s/piato/preview/%s' % (base, o.preview_token))
        print('  Δημόσιο QR:        %s/piato/%s' % (base, o.qr_token))
        print('=' * 60)
        print('⚠️  Ελληνικά = ΜΕΤΑΦΡΑΣΗ Cowork · Αλλεργιογόνα = DRAFT. Επαλήθευση F&B πριν τη δημοσίευση.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
