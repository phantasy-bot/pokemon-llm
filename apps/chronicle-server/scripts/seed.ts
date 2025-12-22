import { insertDrop } from '../src/db';
import { v4 as uuidv4 } from 'uuid';

console.log('Seeding database...');

const drops = [
  {
    name: "Lass Defeats Brock! [Rock Badge]",
    symbol: "LLP-042",
    description: "Omg we actually did it!! T_T Pikachu was struggling so hard against Onix (rock type is scary >_<) but we kited and spammed Tail Whip until we won! The Boulder Badge looks so shiny on my trainer card! *sparkle*",
    publicImageUrl: "/placeholder.png",
    coinAddress: "0x1234567890123456789012345678901234567890",
    hasExclusive: true,
    marketCap: "15420000000000000000",
    volume24h: "2500000000000000000",
    priceChange24h: 24.5,
    hoursAgo: 2
  },
  {
    name: "Caught Jigglypuff <3",
    symbol: "LLP-041",
    description: "Look who I found on Route 3!! It's so round and pink! <3 I almost fainted it by accident but we threw a Great Ball just in time. Now I have a singing buddy! ~la la la~",
    publicImageUrl: "/placeholder.png",
    coinAddress: "0x2222222222222222222222222222222222222222",
    hasExclusive: false,
    marketCap: "500000000000000000",
    volume24h: "100000000000000000",
    priceChange24h: -3.2,
    hoursAgo: 5
  },
  {
    name: "New Route: Mt. Moon",
    symbol: "LLP-040",
    description: "Entering the dark caves... it's kinda spooky in here! O_o Zubats keep swooping at my hair! I hope we find the exit soon... or maybe some rare moon stones? *shiver*",
    publicImageUrl: "/placeholder.png",
    coinAddress: "0x3333333333333333333333333333333333333333",
    hasExclusive: false,
    marketCap: "800000000000000000",
    volume24h: "200000000000000000",
    priceChange24h: 8.7,
    hoursAgo: 8
  },
  {
    name: "Evolution: Pidgeotto ^_^",
    symbol: "LLP-039",
    description: "My little Pidgey grew up!! :) It happened right after the battle with Bug Catcher Sammy. The wingspan is huge now! We're gonna fly so high one day! [Level Up!]",
    publicImageUrl: "/placeholder.png",
    coinAddress: "0x4444444444444444444444444444444444444444",
    hasExclusive: true,
    marketCap: "4200000000000000000",
    volume24h: "1200000000000000000",
    priceChange24h: 42.0,
    hoursAgo: 12
  },
  {
    name: "Stream Start: Kanto Run",
    symbol: "LLP-001",
    description: "Hiii everyone! /wave Lass here! I'm starting my very first Pokemon journey today in Kanto! I'm super nervous but Professor Oak said I have potential! Wish me luck! <3",
    publicImageUrl: "/placeholder.png",
    coinAddress: "0x5555555555555555555555555555555555555555",
    hasExclusive: true,
    marketCap: "10000000000000000000",
    volume24h: "5000000000000000000",
    priceChange24h: 156.8,
    hoursAgo: 48
  }
];

// Generate fillers with cuter text and varied price changes
const fillerActivities = [
    "Just walked through some tall grass! *rustle*",
    "Healed up at the Pokemon Center. Nurse Joy is so nice! <3",
    "Bought some potions at the Mart! [Item Acquired]",
    "Found a hidden item! *ding*",
    "Battled a Youngster! He talked about shorts! :)",
    "My feet hurt from walking... ;_;",
    "Saw a Butterfree flying by! ^_^",
    "Checking my Pokedex... [Loading]"
];

const fillerPriceChanges = [1.2, -0.8, 5.5, -2.1, 0.3, -4.7, 3.3, -1.5, 2.8, -0.5];

for (let i = 0; i < 10; i++) {
    drops.push({
        name: `Journal Entry #${30-i}`,
        symbol: `LLP-0${30-i}`,
        description: fillerActivities[i % fillerActivities.length],
        publicImageUrl: "/placeholder.png",
        coinAddress: `0x${i}000000000000000000000000000000000000000`,
        hasExclusive: false,
        marketCap: "100000000000000000",
        volume24h: "50000000000000000",
        priceChange24h: fillerPriceChanges[i],
        hoursAgo: 24 + i
    });
}

// Reset DB first
import db from '../src/db';
db.exec('DELETE FROM drops');

for (const drop of drops) {
  const timestamp = Math.floor(Date.now() / 1000) - (drop.hoursAgo * 3600);
  
  insertDrop.run({
    id: uuidv4(),
    coinAddress: drop.coinAddress,
    name: drop.name,
    symbol: drop.symbol,
    description: drop.description,
    publicImageUrl: drop.publicImageUrl,
    metadataUri: "ipfs://placeholder",
    exclusiveContentPath: drop.hasExclusive ? "/path/to/fake/content" : null,
    marketCap: drop.marketCap,
    volume24h: drop.volume24h,
    priceChange24h: drop.priceChange24h
  });
  
  db.prepare('UPDATE drops SET createdAt = ? WHERE coinAddress = ?').run(timestamp, drop.coinAddress);
}

console.log(`Seeded ${drops.length} drops with price changes.`);
