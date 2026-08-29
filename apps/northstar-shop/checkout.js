/** Checkout funnel. Shipping-cost surprise is the Type B experiment target. */
export const EXPERIMENT = {
  showDeliveryDateEarlier: false,
  rolloutPct: 0,
};

export function shippingStep(cart) {
  return {
    showCost: true,
    showDate: EXPERIMENT.showDeliveryDateEarlier,
    items: cart?.items ?? [],
  };
}
