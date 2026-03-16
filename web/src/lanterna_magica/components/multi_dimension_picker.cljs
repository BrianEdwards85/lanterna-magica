(ns lanterna-magica.components.multi-dimension-picker
  "Per-type multi-select for dimension IDs."
  (:require
   [lanterna-magica.bp :as bp]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]))

(defn multi-dimension-picker
  "Per-type multi-select for dimension IDs.
   Props:
     :selected-ids - flat vector of selected dimension IDs
     :on-toggle    - (fn [id]) called when user toggles a dimension"
  [{:keys [selected-ids on-toggle]}]
  (let [dim-types    @(rf/subscribe [::subs/dimension-types])
        selected-set (set selected-ids)]
    [:div
     (doall (for [dt dim-types]
       (let [type-id (:id dt)
             items   @(rf/subscribe [::subs/dimensions-dropdown-items-no-base type-id])]
         ^{:key type-id}
         [:div {:class "mb-3"}
          [:label.bp6-label {:style {:margin-bottom "6px" :line-height "30px"}}
           (:name dt)]
          [:div {:class "flex flex-wrap gap-2"}
           (doall (for [item items]
             (let [item-id  (:id item)
                   selected (contains? selected-set item-id)]
               ^{:key item-id}
               [bp/tag
                {:interactive true
                 :intent       (when selected "primary")
                 :minimal      (not selected)
                 :on-click     #(on-toggle item-id)}
                (:name item)])))]])))]))
