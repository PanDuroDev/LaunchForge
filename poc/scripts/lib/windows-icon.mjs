export const REQUIRED_WINDOWS_ICO_SIZES = Object.freeze([16, 24, 32, 48, 64, 256]);

export function validateWindowsIcon(input) {
  const bytes = input instanceof Uint8Array ? input : new Uint8Array(input);
  const readU16 = (offset) => bytes[offset] | (bytes[offset + 1] << 8);
  const readU32 = (offset) => (
    bytes[offset] |
    (bytes[offset + 1] << 8) |
    (bytes[offset + 2] << 16) |
    (bytes[offset + 3] << 24)
  ) >>> 0;

  if (bytes.length < 6 || readU16(0) !== 0 || readU16(2) !== 1) {
    throw new Error("Application icon must be a valid Windows ICO file.");
  }
  const count = readU16(4);
  if (count < REQUIRED_WINDOWS_ICO_SIZES.length || bytes.length < 6 + count * 16) {
    throw new Error("Application ICO is missing one or more required image entries.");
  }

  const sizes = new Set();
  for (let index = 0; index < count; index += 1) {
    const offset = 6 + index * 16;
    const width = bytes[offset] || 256;
    const height = bytes[offset + 1] || 256;
    const planes = readU16(offset + 4);
    const bitsPerPixel = readU16(offset + 6);
    const imageBytes = readU32(offset + 8);
    const imageOffset = readU32(offset + 12);
    if (planes !== 1 || bitsPerPixel < 24 || imageBytes === 0 ||
        imageOffset < 6 + count * 16 || imageOffset + imageBytes > bytes.length) {
      throw new Error(`Application ICO entry ${index} has invalid image metadata.`);
    }
    sizes.add(width === height ? width : -1);
  }
  const missing = REQUIRED_WINDOWS_ICO_SIZES.filter((size) => !sizes.has(size));
  if (missing.length > 0) throw new Error(`Application ICO must contain ${missing.join(", ")} pixel layers.`);
  return true;
}
