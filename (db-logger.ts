import { ethers } from "ethers";
import * as crypto from "crypto";
import Database from "better-sqlite3";

const SEAPORT_1_6_ADDRESS = "0x0000000000000068F116a894984e2DB1123eB395";
const RPC_ENDPOINT = "https://eth.llamarpc.com";
const db = new Database("audit-ledger.db");

// Initialize SQLite audit table
db.prepare(`
    CREATE TABLE IF NOT EXISTS seaport_audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blockNumber INTEGER,
        transactionHash TEXT UNIQUE,
        orderHash TEXT,
        offerer TEXT,
        zone TEXT,
        recipient TEXT,
        timestamp TEXT,
        sha256Hash TEXT
    )
`).run();

const ABI = [
    "event OrderFulfilled(bytes32 indexed orderHash, address indexed offerer, address indexed zone, address recipient)"
];

async function persistAuditToDatabase() {
    const provider = new ethers.JsonRpcProvider(RPC_ENDPOINT);
    const contract = new ethers.Contract(SEAPORT_1_6_ADDRESS, ABI, provider);

    const currentBlock = await provider.getBlockNumber();
    const fromBlock = currentBlock - 15;

    console.log(`[AUDIT] Querying blocks ${fromBlock} to ${currentBlock} for SQLite insertion...`);

    const filter = contract.filters.OrderFulfilled();
    const logs = await contract.queryFilter(filter, fromBlock, currentBlock);
    
    const insertStmt = db.prepare(`
        INSERT OR IGNORE INTO seaport_audits 
        (blockNumber, transactionHash, orderHash, offerer, zone, recipient, timestamp, sha256Hash)
        VALUES (@blockNumber, @transactionHash, @orderHash, @offerer, @zone, @recipient, @timestamp, @sha256Hash)
    `);

    let insertedCount = 0;

    for (const log of logs) {
        const parsed = contract.interface.parseLog({ topics: [...log.topics], data: log.data });
        if (parsed) {
            const record = {
                blockNumber: log.blockNumber,
                transactionHash: log.transactionHash,
                orderHash: parsed.args.orderHash,
                offerer: parsed.args.offerer,
                zone: parsed.args.zone,
                recipient: parsed.args.recipient,
                timestamp: new Date().toISOString()
            };

            const sha256Hash = crypto.createHash("sha256").update(JSON.stringify(record, Object.keys(record).sort())).digest("hex");
            
            try {
                insertStmt.run({ ...record, sha256Hash });
                insertedCount++;
                console.log(`[PASS] Indexed Tx to SQLite: ${log.transactionHash}`);
            } catch (dbError: any) {
                console.error(`[SKIP] Record already exists or failed: ${dbError.message}`);
            }
        }
    }

    console.log(`[DATABASE SYNC COMPLETE] Successfully committed ${insertedCount} new records to audit-ledger.db.`);
}

persistAuditToDatabase();
