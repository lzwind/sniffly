-- Migration: Add messages column to shares table
-- Run this if shares.messages column is missing

ALTER TABLE shares ADD COLUMN messages JSON NOT NULL DEFAULT ('[]');
