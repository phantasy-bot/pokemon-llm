import db from '../src/db';

console.log('Resetting database...');
db.exec('DELETE FROM drops');
console.log('✅ Database reset complete.');
