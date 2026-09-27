export const cultivatedCropSummary = (crops = []) => (
  crops.map((crop) => crop.name).filter(Boolean).join(', ') || null
);

export const farmerSelectedCrops = (crops = []) => (
  crops.filter((crop) => crop.added_by === 'user')
);
