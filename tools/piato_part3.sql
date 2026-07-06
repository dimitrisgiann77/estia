-- PIATO 3/3 - Cohilia (pool bar)
DO $$
DECLARE v_hotel int; v_outlet int; v_cat int; v_item int;
BEGIN
  SELECT id INTO v_hotel FROM hotel WHERE name ILIKE '%asterias%' ORDER BY id LIMIT 1;
  IF v_hotel IS NULL THEN RAISE EXCEPTION 'Asterias not found'; END IF;
  SELECT id INTO v_outlet FROM piato_outlet WHERE hotel_id=v_hotel AND name='Cohilia' ORDER BY id LIMIT 1;
  IF v_outlet IS NULL THEN
    INSERT INTO piato_outlet (hotel_id,name,otype,hours,qr_token,preview_token,published,sort,created_at,updated_at)
    VALUES (v_hotel,'Cohilia','pool_bar','10:00 - 18:00',md5(random()::text||clock_timestamp()::text),md5(random()::text||clock_timestamp()::text||'p'),false,1,now(),now()) RETURNING id INTO v_outlet;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Omeletes"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Omeletes"}','',true,1,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Simple"}','{"en": "Cured ham, cheese"}',6.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Special"}','{"en": "Cheese, Ham, Bacon, Sausage, Peppers, Onion"}',8.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Vegetarian"}','{"en": "Peppers, Onion, Tomatoes, Olives, Mushroom"}',8.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Pizzas"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Pizzas"}','',true,2,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Margarita"}','{"en": "Mozzarella, Tomato sauce"}',8.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Simple"}','{"en": "Mozzarella, Tomato sauce, Cured ham"}',8.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mediterranean"}','{"en": "Mozzarella, Tomato sauce, Onion, Olives, Feta cheese"}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Special"}','{"en": "Mozzarella, Tomato sauce, Pepperoni, Ham, Bacon, Peppers, Onion"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Salads"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Salads"}','',true,3,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Mixed Green"}','{"en": "Lettuce, Cherry tomatoes, Extra virgin olive vinaigrette"}',7.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Greek"}','{"en": "Tomatoes, Cucumber, Peppers, Onion, Lettuce, Olives, Feta cheese"}',7.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Tuna"}','{"en": "Tuna fillets, Onion, Lettuce, Edam cheese, Egg, Cocktail sauce"}',9.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','fish','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Caesar"}','{"en": "Lettuce, Cheese, Grilled Chicken, Tomatoes, Bacon, Crouton, Caesar sauce"}',10.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Toast – Baquettes – Tortillas"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Toast – Baquettes – Tortillas"}','',true,4,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Clasic Toast"}','{"en": "Ham and Cheese"}',4.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Turkey"}','{"en": "Turkey and Cheese"}',4.50,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "B.L.T. Baquette"}','{"en": "Smoked Bacon, Lettuce, Tomato, Mayo"}',6.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Traditional Baquette"}','{"en": "Lettuce, Tomato, Onion, Cucumber, Feta cheese, Peppers"}',7.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Baquette"}','{"en": "Grilled Chicken, Bacon, Cheese, Tomatoes, Bbq Sauce"}',10.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Tuna Tortilla"}','{"en": "Tuna fillets, Onion, Lettuce, Edam cheese, Mayo"}',8.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','fish','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Tortilla"}','{"en": "Lettuce, Cheese, Grilled Chicken, Tomatoes, Caesar sauce"}',9.00,'',true,7,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Club Sandwich"}','{"en": "Lettuce, Cheese, Ham, Tomatoes, Bacon, Mayo"}',10.00,'',true,8,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Club"}','{"en": "Lettuce, Cheese, Ham, Grilled Chicken, Tomatoes, Bacon, Mayo"}',11.00,'',true,9,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Burgers"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Burgers"}','',true,5,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Hamburger"}','{"en": "Beef patty, Lettuce, Tomato, Onion, Mustard, Ketchup"}',7.50,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','mustard');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Cheeseburger"}','{"en": "Beef patty, Cheese, Lettuce, Tomato, Onion, Cocktail sauce"}',8.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Texas"}','{"en": "Beef patty, Lettuce, Tomato, Double Bacon, Onion, Bbq Sauce"}',8.50,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Burger"}','{"en": "Crispy Chicken, Bacon, Cheese, Tomatoes, Caesar sauce"}',9.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('eggs','gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Greek Burger"}','{"en": "Lettuce, Crispy Chicken, Tomatoes, Tzatziki Sauce"}',9.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "Meals & Sides"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "Meals & Sides"}','',true,6,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Grilled Chicken Fillet"}','{"en": "Chips on the side"}',12.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": "Chips and salad on the side"}',9.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Pork Gyros"}','{"en": "Pita bread, Chips, Tomato, Onion, Yogurt"}',10.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Tzatziki"}','{"en": "Pita bread on the side"}',5.00,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "French Fries"}','{"en": ""}',5.00,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Dirty Fries"}','{"en": "Cheddar Cheese, and bacon"}',6.00,'',true,6,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('milk');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM piato_category WHERE outlet_id=v_outlet AND name_i18n='{"en": "For Our Little Friends"}') THEN
    INSERT INTO piato_category (outlet_id,name_i18n,hours,active,sort,created_at,updated_at) VALUES (v_outlet,'{"en": "For Our Little Friends"}','',true,7,now(),now()) RETURNING id INTO v_cat;
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Chicken Nuggets"}','{"en": ""}',6.00,'',true,1,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Fish Fingers"}','{"en": ""}',6.00,'',true,2,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('fish','gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Junior Hamburger"}','{"en": ""}',7.00,'',true,3,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Junior Cheeseburger"}','{"en": ""}',7.50,'',true,4,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten','milk');
    INSERT INTO piato_item (category_id,title_i18n,desc_i18n,price,photo_url,available,sort,created_at,updated_at) VALUES (v_cat,'{"en": "Junior Chicken Burger"}','{"en": ""}',7.50,'',true,5,now(),now()) RETURNING id INTO v_item;
    INSERT INTO piato_item_allergen (item_id,allergen_id) SELECT v_item,id FROM piato_allergen WHERE code IN ('gluten');
  END IF;
  RAISE NOTICE 'PIATO 3/3 - Cohilia (pool bar) OK';
END $$;
