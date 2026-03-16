(ns lanterna-magica.components.dimension-picker
  "Shared dimension picker — renders a per-type searchable select."
  (:require
   [lanterna-magica.components.select :as sel]
   [lanterna-magica.events :as events]
   [lanterna-magica.subs :as subs]
   [re-frame.core :as rf]))

(defn dimension-picker
  "A per-type searchable select that toggles dimension IDs.
   Props:
     :selected-ids - vec of selected dimension IDs
     :on-toggle    - (fn [id]) called when user picks a dimension"
  [{:keys [selected-ids on-toggle]}]
  (let [dim-types @(rf/subscribe [::subs/dimension-types])]
    [:div
     (doall (for [dt dim-types]
       (let [type-id (:id dt)
             items   @(rf/subscribe [::subs/dimensions-dropdown-items type-id])
             sel-id  (some (set selected-ids) (map :id items))]
         ^{:key type-id}
         [:div {:class "mb-3 flex items-center gap-3"}
          [:label.bp6-label.shrink-0 {:style {:margin 0 :line-height "30px"}}
           (:name dt)]
          [:div.flex-1
           [sel/searchable-select
            {:items            items
             :selected-id      sel-id
             :on-select        on-toggle
             :on-query-change  [::events/search-dimensions-list type-id]
             :on-clear-search  [::events/clear-dimensions-search-results type-id]
             :icon             "tag"
             :placeholder      (str "Select " (:name dt) "...")}]]])))]))
