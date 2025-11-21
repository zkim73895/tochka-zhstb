BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "Instruments" (
	"name"	TEXT NOT NULL,
	"ticker"	TEXT NOT NULL CHECK(ticker GLOB '[A-Z][A-Z]*' AND LENGTH(ticker) >= 2 AND LENGTH(ticker) <= 10) UNIQUE,
	PRIMARY KEY("name")
);
CREATE TABLE IF NOT EXISTS "Orders" (
	"id"	TEXT,
	"status"	INTEGER NOT NULL CHECK("status" >= 0 AND "status" < 5),
	"user_id"	TEXT NOT NULL,
	"timestamp"	REAL NOT NULL,
	"direction"	INTEGER NOT NULL CHECK("direction" IN (0, 1)),
	"ticker"	TEXT NOT NULL,
	"qty"	REAL NOT NULL CHECK("qty" > 0),
	"price"	REAL CHECK("price" > 0),
	"filled"	REAL DEFAULT 0 CHECK("filled" <= "qty"),
	"type"	INTEGER NOT NULL CHECK("type" IN (0, 1)),
	PRIMARY KEY("id"),
	CONSTRAINT "FK_order_instrument" FOREIGN KEY("ticker") REFERENCES "Instruments"("ticker") ON DELETE CASCADE,
	CONSTRAINT "FK_order_user" FOREIGN KEY("user_id") REFERENCES "Users"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "Transactions" (
	"id"	INTEGER,
	"user_id"	TEXT NOT NULL,
	"ticker"	TEXT NOT NULL,
	"direction"	INTEGER NOT NULL CHECK("direction" IN (0, 1)),
	"amount"	REAL NOT NULL CHECK("amount" > 0),
	"price"	REAL NOT NULL CHECK("price" > 0),
	"timestamp"	TEXT NOT NULL,
	PRIMARY KEY("id"),
	CONSTRAINT "FK_transaction_instrument" FOREIGN KEY("ticker") REFERENCES "Instruments"("ticker"),
	CONSTRAINT "FK_transaction_user" FOREIGN KEY("user_id") REFERENCES "Users"("id")
);
CREATE TABLE IF NOT EXISTS "UserBalance" (
	"user_id"	TEXT,
	"ticker"	TEXT,
	"balance"	REAL DEFAULT 0,
	"frozen"	REAL DEFAULT 0 CHECK("frozen" <= "balance"),
	PRIMARY KEY("user_id","ticker"),
	CONSTRAINT "fk_userbalance_ticker" FOREIGN KEY("ticker") REFERENCES "Instruments"("ticker"),
	CONSTRAINT "fk_userbalance_user" FOREIGN KEY("user_id") REFERENCES "Users"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "Users" (
	"id"	TEXT,
	"name"	TEXT NOT NULL,
	"role"	INTEGER NOT NULL CHECK("role" IN (0, 1)),
	"api_key"	TEXT,
	"api_key_hashed"	TEXT NOT NULL DEFAULT 'N/A',
	PRIMARY KEY("id")
);

DELETE FROM Instruments WHERE ticker = 'RUB';
INSERT INTO Instruments (name, ticker) VALUES ('Ruble', 'RUB');

CREATE TRIGGER IF NOT EXISTS order_status_on_fill AFTER UPDATE OF filled ON Orders
BEGIN
--If status = 3 (cancelled), do nothing 
--If filled > 0:
--	If filled = qty (filled completely):
--		set status = 2 (executed)
--	else (filled, but not completely):
--		set status = 1 (part-executed)
--else(filled = 0):
--	set status = 0 (new)
UPDATE Orders SET status = IIF(old.status != 3, IIF(new.filled > 0, IIF(new.filled == new.qty, 1, 2),0), old.status)
WHERE id = new.id;
END;
COMMIT;
