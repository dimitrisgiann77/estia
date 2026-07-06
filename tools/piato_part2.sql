-- PIATO 2/3 - Oliva drinks B (spirits..coffee)
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Asterias not found'; END IF;
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name ILIKE '%oliva%' ORDER BY id LIMIT 1;
  IF v_outlet IS NULL THEN RAISE EXCEPTION 'Oliva not found'; END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Spirits"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Spirits"}','',true,16,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Gordon’s"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Gordon’s Premium Pink"}','{"en": ""}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Hendrick’s"}','{"en": ""}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Smirnoff"}','{"en": ""}',6.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Stoli"}','{"en": ""}',6.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Gray Goose"}','{"en": ""}',10.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Bacardi Carta Bianca"}','{"en": ""}',6.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Havana Black"}','{"en": ""}',7.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Hose Cuervo Silver"}','{"en": ""}',7.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Hose Curvo Gold"}','{"en": ""}',7.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Long Drinks"}','{"en": "Regular | Premium · €8 | €11"}',8.00,'',true,11,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Cocktails"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Cocktails"}','',true,17,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mojito"}','{"en": "White rum, Lime juice, White sugar, Mint leaves, Soda"}',10.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Pina Colada"}','{"en": "Coconut juice, Pineapple and White rum"}',10.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Sex on the Beach"}','{"en": "Vodka, Cranberry juice, and Black raspberry liqueur"}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Caipirinha"}','{"en": "Cachaça, Lime, and Sugar"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Margarita"}','{"en": "Tequila, Lime and Triple sec"}',10.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Daiquiri"}','{"en": "Rum, Lime juice, and Sugar syrup"}',10.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mai Tai"}','{"en": "Rum, Curaçao liqueur, Orgeat syrup, and Lime juice"}',10.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Bramblε"}','{"en": "Gin, Fresh lemon juice, Simple syrup and Creme de murre"}',10.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "White Sangria"}','{"en": "Secret Recipe"}',10.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('sulphites');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Kids Menu"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Kids Menu"}','',true,18,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Spaghetti Napolitana"}','{"en": "With cheese"}',5.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Spaghetti Bolognese"}','{"en": "With cheese"}',6.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": "With chips and a dip of Ketchup"}',6.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Plain Burger"}','{"en": "With chips and a dip of Ketchup"}',6.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Brandy"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Brandy"}','',true,19,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Metaxa 3* 33%"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Metaxa 5* 40%"}','{"en": ""}',7.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Metaxa 7* 38%"}','{"en": ""}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Hennessy Vs"}','{"en": "Cognac 40%"}',14.00,'',true,4,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Whiskey"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Whiskey"}','',true,20,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Johnnie Walker"}','{"en": "Red label Scotch blend 40%"}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Famus Grouse"}','{"en": "Scotch Blend 40%"}',6.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "J&B"}','{"en": "Scotch Blend 40%"}',7.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Ballantine’s"}','{"en": "Scotch Blend 40%"}',7.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Dewar’s"}','{"en": "White label Scotch Blend 40%"}',7.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Cutty Sark"}','{"en": "Scotch Blend 40%"}',7.50,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Jameson"}','{"en": "Irish Blend 40%"}',7.50,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Jack Daniel’s"}','{"en": "Tennessee Bourbon Whiskey old No 7 40%"}',7.50,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chivas Regal 12 12"}','{"en": "Year Old Scotch Blend 40%"}',8.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Dimple"}','{"en": "Scotch Blend 15 Years Old 40%"}',8.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Johnnie Walker"}','{"en": "Black barrel Scotch Blend 12 Years 40%"}',9.00,'',true,11,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Cardhu 12"}','{"en": "Single Malt 12 Year Old Whiskey 40%"}',10.00,'',true,12,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Glenfiddich"}','{"en": "Single Malt 12 Year Old Whiskey 40%"}',13.00,'',true,13,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Lagavulin 16"}','{"en": "single malt Scotch smoked Whiskey 43%"}',15.00,'',true,14,now(),now()) RETURNING id INTO v_item;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Refreshments & Coffee"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Refreshments & Coffee"}','',true,21,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Soft Drinks"}','{"en": ""}',3.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mineral Water 0.5L."}','{"en": ""}',1.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mineral Water 1L."}','{"en": ""}',2.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Sparkling Water 1L."}','{"en": ""}',3.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Ice Tea Lemon/peach"}','{"en": ""}',4.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Amita Juice Orange/apple/cherry/pineapple"}','{"en": ""}',4.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Fresh Orange Juice"}','{"en": ""}',5.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Homemade Lamonade or Sour Cherry"}','{"en": ""}',5.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Milkshake"}','{"en": ""}',5.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Greek Coffee"}','{"en": "Single | Double · €3 | €4"}',3.00,'',true,10,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Espresso"}','{"en": "Single | Double · €3 | €4"}',3.00,'',true,11,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Cappuccino"}','{"en": "Single | Double · €4 | €5"}',4.00,'',true,12,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Freddo Espresso"}','{"en": ""}',3.50,'',true,13,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Freddo Cappuccino"}','{"en": ""}',4.50,'',true,14,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Frappe"}','{"en": "& Ice Cream Frappe · €4 | €5"}',4.00,'',true,15,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Lipton Varius Flavors"}','{"en": ""}',4.00,'',true,16,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Cretan Herbal Tea"}','{"en": ""}',5.00,'',true,17,now(),now()) RETURNING id INTO v_item;
  END IF;
  RAISE NOTICE 'PIATO 2/3 - Oliva drinks B (spirits..coffee) OK';
END $$;
