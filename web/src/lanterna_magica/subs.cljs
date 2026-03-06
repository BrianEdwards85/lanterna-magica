(ns lanterna-magica.subs
  (:require [re-frame.core :as rf]))

;; -- Route ----------------------------------------------------------------

(rf/reg-sub ::current-route      (fn [db _] (:current-route db)))

(rf/reg-sub ::current-route-name
 :<- [::current-route]
 (fn [route _] (-> route :data :name)))

;; -- Entity page state ----------------------------------------------------

(rf/reg-sub ::services-page       (fn [db _] (:services-page db)))
(rf/reg-sub ::environments-page   (fn [db _] (:environments-page db)))
(rf/reg-sub ::shared-values-page  (fn [db _] (:shared-values-page db)))
(rf/reg-sub ::configurations-page (fn [db _] (:configurations-page db)))

;; -- Flat lists for dropdowns ---------------------------------------------

(rf/reg-sub ::all-services     (fn [db _] (:all-services db)))
(rf/reg-sub ::all-environments (fn [db _] (:all-environments db)))

;; -- Dialog state ---------------------------------------------------------

(rf/reg-sub ::service-dialog      (fn [db _] (:service-dialog db)))
(rf/reg-sub ::environment-dialog  (fn [db _] (:environment-dialog db)))
(rf/reg-sub ::shared-value-dialog (fn [db _] (:shared-value-dialog db)))
(rf/reg-sub ::revision-dialog     (fn [db _] (:revision-dialog db)))
(rf/reg-sub ::configuration-dialog (fn [db _] (:configuration-dialog db)))

;; -- Loading / Errors -----------------------------------------------------

(rf/reg-sub ::loading        (fn [db _] (:loading db)))

(rf/reg-sub ::loading?
 :<- [::loading]
 (fn [loading [_ key]] (contains? loading key)))

(rf/reg-sub ::errors         (fn [db _] (:errors db)))

(rf/reg-sub ::error
 :<- [::errors]
 (fn [errors [_ key]] (get errors key)))
