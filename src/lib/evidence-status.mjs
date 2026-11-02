const labels = {
  documented_interpretation: 'تفسير موثق',
  reproduced_observation: 'ملاحظة أعيد التحقق منها',
  scientific_comparison: 'مقارنة علمية محدودة',
  hypothesis: 'فرضية تحتاج إلى اختبار',
  needs_verification: 'تحتاج إلى تحقق',
};
export function evidenceStatusLabel(status) {
  if (!Object.hasOwn(labels, status)) throw new Error(`Unknown evidence status: ${status}`);
  return labels[status];
}
